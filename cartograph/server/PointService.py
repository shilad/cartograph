import json
import logging
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
        for n in metricNames:
            mi = json.loads(config.get('Metrics', n))
            assert(mi['type'] == 'count')
            self.metrics[n] = NormalizedMultinomialMetric(mi['fields'], mi['bins'])

        with pg_cnx(config) as cnx:
            with cnx.cursor('points') as cur:
                cur.itersize = 50000
                cur.execute('select x, y, citylabel, maxzoom, popularity, id from coordinates')
                for i, row in enumerate(cur):
                    self.points[row[5]] = {
                        'x' : float(row[1]),
                        'y' : float(row[0]),
                        'name' : row[2],
                        'zoom' : int(row[3]),
                        'pop' : float(row[4]),
                        'id' : row[5]
                    }
                    if i % 50000 == 0:
                        logger.info('loading basic point data for row %d' % i)

            logger.info('building spatial index...')
            ids = sorted(self.points.keys())
            X = [self.points[id]['x'] for id in ids]
            Y = [self.points[id]['y'] for id in ids]
            pops = [self.points[id]['y'] for id in ids]
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
            if id in self.points:
                results.append(self.points[id])
        return results

    def addLayers(self, builder, layer, z, x, y):
        # Add full city information for top 50
        added = set()
        for p in self.getTilePoints(z, x, y, 50):
            props = { 'id' : p['id'], 'zoom' : p['zoom'], 'pop' : p['pop'] }
            builder.addPoint('cities', p['name'],
                             shapely.geometry.Point(p['x'], p['y']), props)
            added.add(p['id'])

        # Add in extra points without properties for next 500 points
        categorize = self.metrics[layer].assignCategory
        extra = defaultdict(list)
        for p in self.getTilePoints(z, x, y, 500):
            if p['id'] not in added:
                c = categorize(p)
                if c: extra[c].append((p['x'], p['y']))
        for c, coords in extra.items():
            print c, len(coords)
            builder.addMultiPoint('extraPoints', c, coords, { 'group' : c })



if __name__ == '__main__':
    from cartograph import Config

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    Config.initConf('data/conf/simple.txt')
    pd = PointService(Config.get())
    builder = TopoJsonBuilder()
    pd.addLayers(builder, 6, 32, 32, 'gender')
    print builder.toJson()

