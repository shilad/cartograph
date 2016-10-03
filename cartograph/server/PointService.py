import json
import logging
import numpy as np
import sys


from collections import defaultdict

import shapely.geometry

from cartograph import getMetric
from cartograph.PointIndex import PointIndex
from cartograph.Utils import pg_cnx
from cartograph.server.ServerUtils import tileExtent
from cartograph.server.TopoJson import TopoJsonBuilder

logger = logging.getLogger('cartograph.pointdata')

class PointService:
    def __init__(self, config):
        self.points = {}
        self.metrics = {}
        metricNames =  config.get('Metrics', 'active').split()
        self.maxZoom = config.getint('Server', 'vector_zoom')
        self.numMetricPoints = { n : 0 for n in metricNames }
        for n in metricNames:
            js = json.loads(config.get('Metrics', n))
            self.metrics[n] = getMetric(js)

        with pg_cnx(config) as cnx:
            with cnx.cursor('points') as cur:
                cur.itersize = 50000
                cur.execute('select x, y, name, zpop, id from coordinates')
                for i, row in enumerate(cur):
                    self.points[row[4]] = {
                        'x' : float(row[0]),
                        'y' : float(row[1]),
                        'name' : row[2],
                        'zpop' : float(row[3]),
                        'id' : row[4]
                    }
                    if i % 50000 == 0:
                        logger.info('loading basic point data for row %d' % i)

            logger.info('building spatial index...')
            ids = sorted(self.points.keys())
            pops = [-self.points[id]['zpop'] for id in ids]
            X = [self.points[id]['x'] for id in ids]
            Y = [self.points[id]['y'] for id in ids]
            self.index = PointIndex(ids, X, Y, pops)
            logger.info('finished indexing %d points...' % len(X))

            for name in metricNames:
                with cnx.cursor(name + 'points') as cur:
                    m = json.loads(config.get('Metrics', name))
                    fields = m['fields'] + ['smoothed' + f for f in m['fields']]
                    cur.execute('select id, %s from %s' % (', '.join(fields), name))
                    for i, row in enumerate(cur):
                        if i % 50000 == 0:
                            logger.info('loading %s metric data for row %d' % (name, i))
                        id = row[0]
                        if id in self.points:
                            self.numMetricPoints[name] += 1
                            for (f, v) in zip(fields, row[1:]):
                                self.points[id][f] = float(v)

            fieldCounts = defaultdict(int)
            for p in self.points.values():
                for k in p:
                    fieldCounts[k] += 1
            pairs = ['%s=%d' % pair for pair in fieldCounts.items() ]
            logging.info("counts for each field are %s", ', '.join(sorted(pairs)))

    def getPoint(self, id):
        return self.points[id]

    def getAllPoints(self):
        return self.points.values()

    def getTilePoints(self, z, x, y, maxN):
        extent = tileExtent(z, x, y)
        matches = self.index.queryRect(extent[0], extent[1], extent[2], extent[3], maxN)

        results = []
        for (pop, id, x, y) in matches:
            # print pop, id, x, y
            if id in self.points:
                results.append(self.points[id])
        return results

    def addLayers(self, builder, layer, z, x, y):
        metric = self.metrics[layer]
        for p in self.getTilePoints(z, x, y, 50):
            (r, g, b, a) = metric.getColor(p, z)
            def f(x): return int(255 * x)
            color = 'rgba(%d,%d,%d,%.3f)' % (f(r), f(g), f(b), a)
            props = { 'id' : p['id'],
                      'zpop' : p['zpop'],
                      'color' : color,
                      'zoff' : (z - p['zpop'])
                      }
            for f in metric.fields:
                props[f] = p.get(f, 0.0)
            builder.addPoint('cities', p['name'],
                             shapely.geometry.Point(p['x'], p['y']), props)


if __name__ == '__main__':
    from cartograph import Config

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    Config.initConf('data/conf/simple.txt')
    pd = PointService(Config.get())
    for p in pd.getTilePoints(6, 26, 36, 10):
        print p['id'], p['zpop']
        if p['id'] == '12706':
            print p['id'], p['zpop']
    # for p in pd.getTilePoints(6, 27, 37, 1000):
    #     if p['id'] == '13616':
    #         print p['id']
    # builder = TopoJsonBuilder()
    # pd.addLayers(builder, 'gender', 6, 27, 36)
    # pd.addLayers(builder, 'gender', 6, 27, 37)
    # print builder.toJson()

