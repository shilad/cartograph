from collections import OrderedDict

import struct

import Config
import re
import json
import psycopg2
import shapely.wkb
import shapely.wkt
import shapely.geometry
import sys

import yaml

import time

PIXELS_PER_TILE = 256
MAX_ZOOM = 16

class TopoJsonBuilder:
    def __init__(self):
        self.data = OrderedDict()
        self.data['type'] = 'Topology'
        # self.data["transform"] = {"scale": [1, 1], "translate": [0, 0]}
        self.data["objects"] = OrderedDict()
        for layer in 'countries', 'cities', 'contours':
            self.getCollection(layer)
        self.data["arcs"] = []

    def addPoint(self, collectionName, shapeName, shape, props=None):
        if props == None: props = {}
        props['name'] = shapeName
        coll = self.getCollection(collectionName)

        coll['geometries'].append({
          "type": "Point",
          "properties": props,
          "coordinates": [shape.x, shape.y]
        })

    def addMultiPolygon(self, collectionName, shape, props=None):
        if shape.geom_type == 'Polygon': shape = [shape]
        if props == None: props = {}
        coll = self.getCollection(collectionName)

        def mkArc(coords):
            coords = list(coords)
            if coords[0] != coords[-1]: # make sure its a ring
                coords = coords + [coords[0]]
            return [ self.addArc(coords) ]

        arcs = []
        for p in shape:
            a = [ mkArc(p.exterior.coords) ]
            for hole in p.interiors:
                a.append(mkArc(hole.coords))
            arcs.append(a)

        coll['geometries'].append({
          "type": "MultiPolygon",
          "properties": props,
          "arcs": arcs
        })

    def addArc(self, arc):
        self.data['arcs'].append(arc)
        return len(self.data['arcs']) - 1

    def toJson(self, filename=None):
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.data, f)
        else:
            return json.dumps(self.data)

    def getCollection(self, name):
        if not name in self.data['objects']:
            self.data['objects'][name] = OrderedDict()
            self.data['objects'][name]['type'] = 'GeometryCollection'
            self.data['objects'][name]['geometries'] = []

        return self.data['objects'][name]


def warn(message):
    sys.stderr.write(message + '\n')


class PolyLayer:
    def __init__(self, name, table=None, fields=None, simplification=None, labelField=None):
        assert(table and fields and simplification)
        self.name = name
        self.table = table
        self.fields = fields
        self.simplification = simplification
        self.labelField = labelField
        self.cache = {}

    def getFromCache(self, cur, z):
        z = self.getEffectiveZoom(z)
        if not z in self.cache:
            query = 'select %s from %s' % (', ' .join(['geom'] + self.fields), self.table)
            cur.execute(query)
            raw = []
            props = []
            for row in cur:
                props.append(dict(zip(self.fields, row[1:])))
                raw.append(shapely.wkb.loads(row[0], hex=True).buffer(0))
            merged = shapely.geometry.GeometryCollection(raw)
            simplified = list(s.buffer(0) for s in merged.simplify(self.simplification[z]))
            centers = list(s.representative_point() for s in simplified)
            self.cache[z] = zip(simplified, props, centers)
        return self.cache[z]

    def getPolys(self, cur, z):
        polys = self.getFromCache(cur, z)
        result = []
        for shp, prop, center in polys:
            p = dict(prop)
            result.append((
                shp,
                p,
                center
            ))
        return result

    def getPolysInBox(self, cur, z, box):
        polys = self.getFromCache(cur, z)
        width = box.bounds[2] - box.bounds[0]
        print width
        bigBox = box.buffer(1.2 * width)
        result = []
        for shp, prop, center in polys:
            if bigBox.intersects(shp):
                p = dict(prop)
                result.append((
                    box.intersection(shp),
                    p,
                    center if box.contains(center) else None
                ))
        return result


    def getEffectiveZoom(self, z):
        """Returns the highest known zoom that is less than or equal to z"""
        effectiveZ = min(self.simplification.keys())
        for i in range(z+1):
            if i in self.simplification:
                effectiveZ = i
        return effectiveZ


class Server:
    def __init__(self, config):
        self.config = config
        self.cnx = psycopg2.connect(
            dbname=config.get('PG', 'database'),
            host=config.get('PG', 'host'),
            user=config.get('PG', 'user'),
            password=config.get('PG', 'password'),
        )
        self.cached = {}
        # self.getBounds()
        self.simplifications = { 1: 1, 5: 0.1, 10: 0.01}
        self.bound = 180.0
        self.polys = [
            PolyLayer('countries',
                      table='countries',
                      fields=['id', 'labels', 'clusternum'],
                      simplification=self.simplifications,
                      labelField='labels'
                      ),
            PolyLayer('centroid_contours',
                      table='contourscentroid',
                      fields=['id', 'clusternum', 'contournum'],
                      simplification={ 1: 1, 5: 0.5, 10: 0.1 }
                      ),
            PolyLayer('density_contours',
                      table='contoursdensity',
                      fields=['id', 'clusternum', 'contournum'],
                      simplification={ 1: 1, 5: 0.5, 10: 0.1 }
                      ),
        ]

    def getBounds(self):
        with self.cnx.cursor() as cur:
            cur.execute('select ST_extent(geom) from coordinates')
            row = cur.fetchone()
            assert(row)
            pat = re.compile('BOX\\((.*) (.*),(.*) (.*)\\)')
            m = pat.match(row[0])
            assert(m)
            self.bound = max([abs(float(x)) for x in m.groups()])
            warn('setting max bound to %.3f' % self.bound)

    def serve(self, path):
        if path.startswith('/tile'):
            return self.handleTile(path)
        elif path.startswith('/fixed'):
            return self.handleFixed(path)
        elif path.endswith('countries.yaml'):
            return self.handleCountries()
        else:
            return

    def handleCountries(self):
        config = {
            'layers' : {
                'contours' : {
                    'data' : { 'source': 'fixed', 'layer': 'density_contours' }
                },
                'countries': {
                    'data': {'source': 'fixed', 'layer': 'countries'}
                }
            }
        }
        colors = Config.getColorWheel()
        order = 2
        for cluster in colors:
            hex = colors[cluster][7]
            (r, g, b) = struct.unpack('BBB', hex[1:].decode('hex'))
            c = {
                'filter': {'clusternum': cluster},
                'draw': {
                    'polygons': {
                        'color': "rgb(%d,%d,%d)" % (r, g, b),
                        'width': '1px',
                        'order': order,
                        'blend': 'overlay'
                    }
                }
            }

            sublayer = 'country_%d' % (cluster)
            config['layers']['countries'][sublayer] = c

            for contour in colors[cluster]:
                hex = colors[cluster][contour]
                (r, g, b) = struct.unpack('BBB', hex[1:].decode('hex'))
                c = {
                    'filter' : {
                        'all' : [ {'clusternum' : cluster}, {'contournum' : contour}]
                    },
                    'draw' : {
                        'polygons' : {
                            'color' : "rgb(%d,%d,%d)" % (r, g, b),
                            'width' : '1px',
                            'order' : order,
                            'blend' : 'overlay'
                        }
                    }
                }
                sublayer = 'contour_%d_%d' % (cluster, contour)
                config['layers']['contours'][sublayer] = c
                order += 1
        return yaml.dump(config)


    def handleFixed(self, path):
        assert(path.endswith('.topojson'))
        parts = path[1:-len('.topojson')].split('/')
        z = int(parts[1])
        if z in self.cached: return self.cached[z]
        builder = TopoJsonBuilder()
        with self.cnx.cursor() as cur:
            t0 = time.time()
            for poly in self.polys:
                for shp, props, center in poly.getPolys(cur, z):
                    builder.addMultiPolygon(poly.name, shp, props)
                    if poly.labelField:
                        builder.addPoint(poly.name + '_labels', props[poly.labelField], center)
        self.cached[z] = builder.toJson()
        return self.cached[z]

    def handleTile(self, path):
        assert(path.endswith('.topojson'))
        parts = path[1:-len('.topojson')].split('/')
        z, x, y = int(parts[1]), float(parts[2]), float(parts[3])
        extent = self.tileExtent(z, x, y)
        print 'extents for', x, y, z, 'are', extent
        if (z, x, y) in self.cached: return self.cached[z, x, y]
        builder = TopoJsonBuilder()
        # if True:
        #     width = abs(extent[0] - extent[2])
        #     print width
        #     for i in range(4):
        #         for j in range(4):
        #             p = shapely.geometry.Point(extent[0] + width / 4 * i,
        #                                        extent[1] + width / 4 * j)
        #             print extent, p
        #             builder.addPoint('cities', 'point_foo', p, {'city': ('(%.1f,%.1f)' % (p.x, p.y))})
        #     self.cached[z, x, y] = builder.toJson()
        #     return self.cached[z, x, y]

        with self.cnx.cursor() as cur:
            t0 = time.time()
            # for poly in self.polys:
            #     for shp, props in poly.getPolysInBox(cur, z, box):
            #         builder.addMultiPolygon('countries', shp, props)

            t1 = time.time()
            query = """SELECT id, geom, citylabel, popularity, maxzoom from coordinates WHERE maxzoom <= %s and geom && ST_MakeEnvelope%s order by popularity desc limit 50""" % (z+3, tuple(extent),)
            # print 'query is', query
            cur.execute(query)
            cur.itersize = 1000
            t2 = time.time()
            i = 0
            for row in cur:
                props = {'city': row[2], 'pop' : float(row[3]), 'z' : float(z+3-row[4])}
                shp = shapely.wkb.loads(row[1], hex=True)
                builder.addPoint('cities', 'point_' + str(row[0]), shp, props)
                i += 1
            print query, i
            t3 = time.time()

            print('times', (t1 - t0), (t2-t1), (t3-t2))
        self.cached[z, x, y] = builder.toJson()
        return self.cached[z, x, y]

    def tileExtent(self, z, x, y):
        tileGridWidth = 2 ** z
        rangePerTile = 2.0 * self.bound / tileGridWidth
        x0 = x * rangePerTile - self.bound
        y1 = self.bound - y * rangePerTile
        x1 = x0 + rangePerTile
        y0 = y1 - rangePerTile
        return (x0, y0, x1, y1)

    def numTilesAtZoom(self, z):
        return 2**z

if __name__ == '__main__':
    if len(sys.argv) > 2:
        sys.stderr.write('usage: %s {path/to/conf.txt}\n')
        sys.exit(1)

    pathConf = sys.argv[1] if len(sys.argv) == 2 else None
    Config.initConf(pathConf)

    import os

    from werkzeug.wrappers import Request, Response

    server = Server(Config.get())
    print server.serve('/contours')
    server.serve('/tiles/1/0/0.topojson')
    server.serve('/fixed/0.topojson')

    def application(environ, start_response):
        req = Request(environ)
        text = server.serve(req.path)
        resp = Response(text, mimetype='application/json')
        return resp(environ, start_response)

    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }
    print static_files

    from werkzeug.serving import run_simple
    run_simple('localhost', 4000, application, static_files=static_files)
