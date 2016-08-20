from collections import OrderedDict

import re
import json
import psycopg2
import shapely.wkb
import shapely.wkt
import shapely.geometry
import sys

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

        arcs = []
        for p in shape:
            arcs.append([])
            arcs[-1].append([self.addArc(list(p.exterior.coords))])
            for hole in p.interiors:
                arcs[-1].append([self.addArc(list(hole.coords))])

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
    def __init__(self, name, table=None, fields=None, simplification=None):
        assert(table and fields and simplification)
        self.name = name
        self.table = table
        self.fields = fields
        self.simplification = simplification
        self.cache = {}

    def getPolys(self, cur, z, box):
        z = self.getEffectiveZoom(z)
        if not z in self.cache:
            query = 'select %s from %s' % (', ' .join(['geom'] + self.fields), self.table)
            cur.execute(query)
            raw = []
            props = []
            for row in cur:
                props.append(dict(zip(self.fields, row[1:])))
                raw.append(shapely.wkb.loads(row[0], hex=True))
            merged = shapely.geometry.GeometryCollection(raw)
            simplified = list(merged.simplify(self.simplification[z]))
            self.cache[z] = zip(simplified, props)

        result = []
        for shp, prop in self.cache[z]:
            if box.intersects(shp):
                result.append((
                    box.intersection(shp),
                    prop
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
        self.cnx = psycopg2.connect(dbname='mapnik_dev_en', host='localhost')
        self.cached = {}
        # self.getBounds()
        self.simplifications = { 1: 0.1, 5: 0.01, 10: 0.001}
        self.bound = 180.0
        self.polys = [
            PolyLayer('countries',
                      table='countries',
                      fields=['id', 'labels'],
                      simplification=self.simplifications)
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
        if not path.startswith('/tile'): return
        assert(path.endswith('.topojson'))
        parts = path[1:-len('.topojson')].split('/')
        z, x, y = int(parts[2]), float(parts[3]), float(parts[4])
        extent = self.tileExtent(z, x, y)
        width = extent[0] - extent[2]
        box = apply(shapely.geometry.box, extent)
        # box = box.buffer(0.1 * width)
        # print z, x, y, extent, box
        if (z, x, y) in self.cached: return self.cached[z, x, y]
        builder = TopoJsonBuilder()
        with self.cnx.cursor() as cur:
            t0 = time.time()
            for poly in self.polys:
                for shp, props in poly.getPolys(cur, z, box):
                    builder.addMultiPolygon('countries', shp, props)

            t1 = time.time()
            query = """SELECT id, geom, citylabel from coordinates WHERE maxzoom <= %s and geom && ST_MakeEnvelope%s""" % (z+5, tuple(extent),)
            print query
            # print 'query is', query
            cur.execute(query)
            cur.itersize = 1000
            t2 = time.time()
            for row in cur:
                shp = shapely.wkb.loads(row[1], hex=True)
                builder.addPoint('cities', 'point_' + str(row[0]), shp, {'city': row[2]})
            t3 = time.time()

            print('times', (t1 - t0), (t2-t1), (t3-t2))
        self.cached[z, x, y] = builder.toJson()
        # print self.cached[z, x, y]
        return self.cached[z, x, y]

    def tileExtent(self, z, x, y):
        tileGridWidth = 2 ** z
        rangePerTile = 2.0 * self.bound / tileGridWidth
        x0 = x * rangePerTile - self.bound
        y0 = y * rangePerTile - self.bound
        x1 = x0 + rangePerTile
        y1 = y0 + rangePerTile
        return (x0, y0, x1, y1)

    def numTilesAtZoom(self, z):
        return 2**z

if __name__ == '__main__':
    import os
    from werkzeug.wrappers import Request, Response

    server = Server(None)
    print server.serve('/tiles/all/1/0/0.topojson')

    def application(environ, start_response):
        req = Request(environ)
        text = server.serve(req.path)
        resp = Response(text, mimetype='application/json')
        return resp(environ, start_response)

    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }
    print static_files

    from werkzeug.serving import run_simple
    run_simple('localhost', 4000, application, static_files=static_files)
