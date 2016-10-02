import json
import logging
import numpy as np
import sys


from collections import defaultdict

import shapely.geometry

from cartograph.NormalizedMultinomialMetric import NormalizedMultinomialMetric
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
            mi = json.loads(config.get('Metrics', n))
            assert(mi['type'] == 'count')
            self.metrics[n] = NormalizedMultinomialMetric(mi['fields'], mi['colors'], mi['bins'])

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
        # Add full city information for top 50
        added = set()

        # Add in extra points without properties for next 500 points
        metric = self.metrics[layer]
        colors = metric.getColors(z)
        for group in colors.keys():
            for zoom in colors[group].keys():
                (r, g, b, a) = colors[group][zoom]
                def f(x): return int(255 * x)
                colors[group][zoom] = 'rgba(%d,%d,%d,%.3f)' % (f(r), f(g), f(b), a)

        for p in self.getTilePoints(z, x, y, 50):
            props = { 'id' : p['id'],
                      'zpop' : p['zpop'],
                      'zoff' : (z - p['zpop'])
                      }
            g = metric.assignCategory(p)
            if g:
                zp = int(p['zpop'])
                props['group'] = g
                props['color'] = colors[g][zp]
            for f in metric.fields:
                props[f] = p.get(f, 0.0)
            builder.addPoint('cities', p['name'],
                             shapely.geometry.Point(p['x'], p['y']), props)
            added.add(p['id'])

        if z < self.maxZoom:
            return

        extra = defaultdict(list)
        for p in self.getTilePoints(z, x, y, 1000):
            if p['id'] not in added:
                c = metric.assignCategory(p)
                if not c: c = ''
                zp = int(p['zpop'])
                extra[c, zp].append((p['x'], p['y']))
        for (c, zp), coords in extra.items():
            props = {
                'group' : c,
                'zpop' : zp,
                'zoff' : (z - zp)
             }
            if c: props['color'] = colors[c][zp]
            builder.addMultiPoint('extraPoints', c, coords, props)



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

