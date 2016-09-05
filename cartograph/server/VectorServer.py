import re
import struct
import sys
import threading
import time

import psycopg2
import shapely.geometry
import shapely.wkb
import shapely.wkt
import yaml

import cartograph.Config

from EdgeLayer import EdgeLayer
from TopoJson import TopoJsonBuilder
from PolyLayer import PolyLayer
from Search import Search
from globalmaptiles import GlobalMercator


def warn(message):
    sys.stderr.write(message + '\n')


class Server:
    def __init__(self, config):
        self.config = config
        self.cnx = psycopg2.connect(
            dbname=config.get('PG', 'database'),
            host=config.get('PG', 'host'),
            user=config.get('PG', 'user'),
            password=config.get('PG', 'password'),
        )
        self.search = Search(self.config, self.cnx)
        self.mercator = GlobalMercator()
        self.cache = {}
        self.cacheLock = threading.Lock()
        # self.getBounds()
        self.simplifications = { 1: .5, 5: 0.1, 7: .01, 10: 0.001}
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
        self.edges = EdgeLayer(config, self.cnx)

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

    def serve(self, path, req=None):
        if '/tile/' in path:
            return self.handleTile(path)
        elif '/fixed' in path:
            return self.handleFixed(path)
        elif path.endswith('/search'):
            return self.handleSearch(req)
        elif path.endswith('countries.yaml'):
            return self.handleCountries()
        else:
            return

    def handleCountries(self):
        config = {
            'styles' : {
                'poly-alpha' : {
                    'base': 'polygons',
                    'blend_order': 0,
                    'blend': 'overlay'
                }

            },
            'layers' : {
                'contours' : {
                    'data' : { 'source': 'tiled', 'layer': 'density_contours' }
                },
                'countries': {
                    'data': {'source': 'tiled', 'layer': 'countries'}
                }
            }
        }
        colors = cartograph.Config.getColorWheel()
        order = 2
        for cluster in colors:
            hex = colors[cluster][7]
            (r, g, b) = struct.unpack('BBB', hex[1:].decode('hex'))
            c = {
                'filter': {'clusternum': cluster},
                'draw': {
                    'polygons': {
                        'color': "rgb(%d,%d,%d)" % (r, g, b),
                        # 'style': 'poly-alpha',
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
                            # 'style': 'poly-alpha',
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

    def handleSearch(self, req):
        return self.search.search(req.args['q'], 10)

    def getFromCache(self, key):
        self.cacheLock.acquire()
        try:
            return self.cache.get(key)
        finally:
            self.cacheLock.release()

    def addToCache(self, key, val):
        self.cacheLock.acquire()
        try:
            self.cache[key] = val
        finally:
            self.cacheLock.release()
        return val

    def handleFixed(self, path):
        assert(path.endswith('.topojson'))
        parts = path[:-len('.topojson')].split('/')
        z = int(parts[-1])
        v = self.getFromCache(z)
        if v:
            return v
        builder = TopoJsonBuilder()
        with self.cnx.cursor() as cur:
            for poly in self.polys:
                for shp, props, center in poly.getPolys(cur, z):
                    builder.addMultiPolygon(poly.name, shp, props)
                    if poly.labelField:
                        builder.addPoint(poly.name + '_labels', props[poly.labelField], center)
        return self.addToCache(z, builder.toJson())

    def handleTile(self, path):
        assert(path.endswith('.topojson'))
        parts = path[:-len('.topojson')].split('/')
        print parts
        z, x, y = int(parts[-3]), float(parts[-2]), float(parts[-1])
        extent = self.tileExtent(z, x, y)
        val = self.getFromCache((z, x, y))
        if val:
            return val
        builder = TopoJsonBuilder()

        with self.cnx.cursor() as cur:
            t0 = time.time()

            (x0, y0, x1, y1) = extent
            assert(x0 <= x1)
            assert(y0 <= y1)
            delta = abs(x0 - x1) * 0.1
            # print extent
            box = shapely.geometry.box(x0 - delta, y0 - delta, x1 + delta, y1 + delta)
            # box = shapely.geometry.box(x0, y0, x1, y1)
            # print box
            for poly in self.polys:
                for shp, props, center in poly.getPolysInBox(cur, z, box):
                    if center and poly.labelField:
                        builder.addPoint('countries_labels', props[poly.labelField], center)
                    builder.addMultiPolygon(poly.name, shp, props)

            t1 = time.time()
            query = """SELECT id, geom, citylabel, popularity, maxzoom from coordinates WHERE maxzoom <= %s and geom && ST_MakeEnvelope%s order by popularity desc limit 50""" % (z+3, tuple(extent),)
            # print 'query is', query
            cur.execute(query)
            cur.itersize = 1000
            t2 = time.time()
            i = 0
            for row in cur:
                props = {'city': row[2], 'pop' : float(row[3]), 'zoomOffset' : int(z+3-row[4])}
                shp = shapely.wkb.loads(row[1], hex=True)
                builder.addPoint('cities', 'point_' + str(row[0]), shp, props)
                i += 1
            # print query, i
            t3 = time.time()
            # for ei in self.edges.getEdges(tuple(extent), z):
            #     builder.addMultiLine('edges', ei['bundle'])
            t4 = time.time()

            # print('times', (t1 - t0), (t2-t1), (t3-t2))

        if False:
            (x0, y0, x1, y1) = extent
            delta = abs(x0 - x1) * 0.02
            print extent
            box = shapely.geometry.box(x0 + delta, y0 + delta, x1 - delta, y1 - delta)
            builder.addMultiPolygon('tiles', box)
            builder.addPoint('tile_labels', '(%d/%d/%d - %s)' % (z, x, y, box.centroid), box.centroid)

        return self.addToCache((z, x, y), builder.toJson())

    def tileExtent(self, z, x, y):
        tx = x
        ty = 2**z - 1 - y   # tms coordinates
        (lat0, long0, lat1, long1) = self.mercator.TileLatLonBounds(tx, ty, z)
        return (long0, lat0, long1, lat1)

    def numTilesAtZoom(self, z):
        return 2**z

if __name__ == '__main__':
    if len(sys.argv) > 2:
        sys.stderr.write('usage: %s {path/to/conf.txt}\n')
        sys.exit(1)

    pathConf = sys.argv[1] if len(sys.argv) == 2 else None
    cartograph.Config.initConf(pathConf)

    import os

    from werkzeug.wrappers import Request, Response

    server = Server(cartograph.Config.get())
    # print server.search.search('App')
    # print server.serve('/contours')
    print server.serve('/tile/6/32/25.topojson')
    # server.serve('/fixed/0.topojson')

    # for z in range(11):
    #     total = 0
    #     for x in range(2**z):
    #         print 'doing', z, x, total
    #         for y in range(2**z):
    #             extent = server.tileExtent(z, x, y)
    #             if extent[0] > 40 or extent[1] > 40 or extent[2] < -40 or extent[3] < -40:
    #                 continue
    #             l = len(server.serve('/tiles/6/%d/%d.topojson' % (x, y)))
    #             total += l
    #             # print z, x, y, extent, l


    def application(environ, start_response):
        req = Request(environ)
        text = server.serve(req.path, req)
        resp = Response(text, mimetype='application/json')
        return resp(environ, start_response)

    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    from werkzeug.serving import run_simple
    run_simple('localhost', 4000, application, static_files=static_files)
