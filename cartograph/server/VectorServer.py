import re
import struct
import sys
import threading
import time

import math
import psycopg2
import shapely.geometry
import shapely.wkb
import shapely.wkt
import shutil
import yaml

import cartograph.Config

from EdgeLayer import EdgeLayer
from TopoJson import TopoJsonBuilder
from PolyLayer import PolyLayer
from Search import Search
from cartograph.server.MapnikServer import MapnikServer
from globalmaptiles import GlobalMercator


def warn(message):
    sys.stderr.write(message + '\n')


def inscribePoly(box, n=8):
    bounds = box.bounds
    center = box.centroid
    radius = max(bounds[2] - bounds[0], bounds[3] - bounds[1]) / 2.0
    points = []
    for i in range(n):
        a = 2 * math.pi / n * i
        points.append((
            center.x + math.cos(a) * radius,
            center.y + math.sin(a) * radius
        ))
    points.append(points[0])
    return shapely.geometry.Polygon(points)


class Server:
    def __init__(self, config):
        self.config = config
        self.cnx = psycopg2.connect(
            dbname=config.get('PG', 'database'),
            host=config.get('PG', 'host'),
            user=config.get('PG', 'user'),
            password=config.get('PG', 'password'),
        )
        self.rasters = {}
        for name in ['base'] + config.get('Metrics', 'active').split():
            xmlFile = config.get('DEFAULT', 'mapDir') + '/' + name + '.xml'
            self.rasters[name] = MapnikServer(xmlFile)

        self.search = Search(self.config, self.cnx)
        self.mercator = GlobalMercator()
        self.cache = {}
        self.coords = {}
        self.cacheLock = threading.Lock()
        # self.getBounds()
        self.simplifications = { 1: .2, 7: .05, 10: 0.01}
        self.bound = 180.0
        self.polys = [
            PolyLayer('countries',
                      table='countries',
                      fields=['labels', 'clusterid'],
                      simplification=self.simplifications,
                      labelField='labels'
                      ),
            PolyLayer('centroid_contours',
                      table='contourscentroid',
                      fields=['clusterid', 'contournum', 'contourid'],
                      simplification=self.simplifications,
                      ),
            PolyLayer('density_contours',
                      table='contoursdensity',
                      fields=['clusterid', 'contournum', 'contourid'],
                      simplification=self.simplifications,
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
        print path
        if '/tile/' in path:
            return self.handleTile(path)
        elif '/fixed' in path:
            return self.handleFixed(path)
        elif '/raster' in path:
            return self.handleRaster(path)
        elif '/metricPoints' in path:
            return self.handleMetricPoints(path)
        elif '/metric' in path:
            return self.handleMetric(path)
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
                    'data' : { 'source': 'tiled', 'layer': 'centroid_contours' },
                    'filter': { '$zoom': { 'min': 6 } }
                },
                'countries': {
                    'data': {'source': 'tiled', 'layer': 'countries'},
                    'filter': { '$zoom': { 'min': 6 } }
                }
            }
        }
        colors = cartograph.Config.getColorWheel()
        order = 2
        for cluster in colors:
            hex = colors[cluster][7]
            (r, g, b) = struct.unpack('BBB', hex[1:].decode('hex'))
            c = {
                'filter': {'clusterid': cluster},
                'draw': {
                    'polygons': {
                        'color': "rgb(%d,%d,%d)" % (r, g, b),
                        # 'style': 'poly-alpha',
                        'width': '1px',
                        'order': order,
                        'blend': 'inlay'
                    }
                }
            }

            sublayer = 'country_' + cluster
            config['layers']['countries'][sublayer] = c

            for contour in colors[cluster]:
                hex = colors[cluster][contour]
                (r, g, b) = struct.unpack('BBB', hex[1:].decode('hex'))
                c = {
                    'filter' : { 'contourid' : '%s_%s' % (cluster, contour) },
                    'draw' : {
                        'polygons' : {
                            'color' : "rgb(%d,%d,%d)" % (r, g, b),
                            # 'style': 'poly-alpha',
                            'width' : '1px',
                            'order' : order,
                            'blend' : 'inlay'
                        }
                    }
                }
                sublayer = 'contour_%s_%s' % (cluster, contour)
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
            # box = shapely.geometry.box(y0 - delta, x0 - delta, y1 + delta, x1 + delta)
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

    def handleMetricPoints(self, path):
        assert(path.endswith('.topojson'))
        parts = path[:-len('.topojson')].split('/')
        m, z, x, y = parts[-4], int(parts[-3]), float(parts[-2]), float(parts[-1])
        val = self.getFromCache((m, z, x, y))
        if val:
            return val

        extent = self.tileExtent(z, x, y)
        builder = TopoJsonBuilder()

        with self.cnx.cursor() as cur:
            t0 = time.time()
            t1 = time.time()
            query = """SELECT * from %s where geom && ST_MakeEnvelope%s """ % (m, extent)
            cur.itersize = 1000
            # print 'query is', query
            cur.execute(query)
            colnames = [desc[0] for desc in cur.description]
            idCol = colnames.index('id')
            geomCol = colnames.index('geom')
            t2 = time.time()
            i = 0
            for row in cur:
                id = row[idCol]
                props = {}
                for k, v in zip(colnames, row):
                    if v is not None and k not in ('id', 'geom'):
                        props[k] = float(v)
                if props:
                    shp = shapely.wkb.loads(row[geomCol], hex=True)
                    builder.addPoint(m, id, shp, props)
                    i += 1
            # print query, i
            t3 = time.time()
            # for ei in self.edges.getEdges(tuple(extent), z):
            #     builder.addMultiLine('edges', ei['bundle'])
            t4 = time.time()

            # print('times', (t1 - t0), (t2-t1), (t3-t2))

        return self.addToCache((m, z, x, y), builder.toJson())


    def handleRaster(self, path):
        assert(path.endswith('.png'))
        parts = path[:-len('.png')].split('/')
        m, z, x, y = parts[-4], int(parts[-3]), float(parts[-2]), float(parts[-1])
        path = os.path.join(self.config.get('DEFAULT', 'tileDir'), m, str(z), str(x))
        if not os.path.isdir(path):
            os.makedirs(path)
        path += str(y) + '.png'
        path = path.encode('ascii', 'ignore')
        if not os.path.isfile(path):
            self.rasters[m].render_tile(path, x, y, z)
        with open(path) as f:
            return f.read()

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

    conf = cartograph.Config.get()
    shutil.rmtree(conf.get('DEFAULT', 'tileDir'), ignore_errors=True)

    from werkzeug.wrappers import Request, Response

    server = Server(cartograph.Config.get())
    print server.handleMetricPoints('/metricPoints/gender/6/32/32.topojson')
    # print server.handleRaster('/raster/gender/6/32/32.png')
    # print server.search.search('App')
    # print server.serve('/contours')
    # print server.serve('/tile/6/32/25.topojson')
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
        if req.path.endswith('.png'):
            resp = Response(text, mimetype='image/png')
        else:
            resp = Response(text, mimetype='application/json')
        return resp(environ, start_response)

    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    from werkzeug.serving import run_simple
    run_simple('localhost', 4000, application, static_files=static_files)

