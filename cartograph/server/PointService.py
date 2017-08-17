import json
import logging
import sys


from collections import defaultdict

import shapely.geometry


from cartograph import getMetric
from cartograph.PointIndex import PointIndex
from cartograph.Utils import read_features
from cartograph.metrics.ClusterMetric import ClusterMetric
from cartograph.server.ServerUtils import tileExtent
from cartograph.server import RelatedPointsService

logger = logging.getLogger('cartograph.pointdata')

class PointService:
    def __init__(self, config):
        self.points = {}
        self.metrics = {'cluster' : ClusterMetric(config) }
        self.maxZoom = config.getint('Server', 'vector_zoom')

        self.points = read_features(
            config.get('GeneratedFiles', 'article_coordinates'),
            config.get('GeneratedFiles', 'zpop_with_id'),
            config.get('GeneratedFiles', 'clusters_with_id'),
            config.get('ExternalFiles', 'names_with_id'),
            required=('x', 'y', 'zpop', 'name', 'cluster')
        )

        for (id, point) in self.points.items():
            point['x'] = float(point['x'])
            point['y'] = float(point['y'])
            point['zpop'] = float(point['zpop'])
            point['clusterid'] = point['cluster']
            point['id'] = id
            point['skipped'] = point['name'] and point['name'].strip()[-1] in 'abcdefghijk'

        logger.info('building spatial index...')
        ids = sorted(self.points.keys())
        pops = [-self.points[id]['zpop'] for id in ids]
        X = [self.points[id]['x'] for id in ids]
        Y = [self.points[id]['y'] for id in ids]
        self.index = PointIndex(ids, X, Y, pops)
        logger.info('finished indexing %d points...' % len(X))

        metricNames =  config.get('Metrics', 'active').split()
        self.numMetricPoints = { n : 0 for n in metricNames }
        for n in metricNames:
            js = json.loads(config.get('Metrics', n))
            self.metrics[n] = getMetric(js)

        metricDir = config.get('DEFAULT', 'metricDir')
        for name, m in self.metrics.items():
            if name == 'cluster': continue
            for line in open('%s/%s.json' % (metricDir, name), 'r'):
                js = json.loads(line)
                id = js.get('id')
                if id in self.points:
                    for (k, v) in js.items():
                        if k != 'id':
                            self.points[id][k]= v

            if hasattr(m, 'train'):
                m.train(self.points.values())

        fieldCounts = defaultdict(int)
        for p in self.points.values():
            for k in p:
                fieldCounts[k] += 1
        pairs = ['%s=%d' % pair for pair in fieldCounts.items() ]
        logging.info("counts for each field are %s", ', '.join(sorted(pairs)))

    def hasPoint(self, id):
        return id in self.points

    def getPoint(self, id):
        return self.points[id]

    def getAllPoints(self):
        return self.points.values()

    def getNumPoints(self):
        return len(self.points)

    def getTilePoints(self, z, x, y, maxN):
        extent = tileExtent(z, x, y)
        matches = self.index.queryRect(extent[0], extent[1], extent[2], extent[3], maxN)
        results = []
        for (pop, id, x, y) in matches:
            # print pop, id, x, y
            # print(self.points[id]['skipped'])
            # if id in self.points and not self.points[id]['skipped']:
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
    from cartograph import MapConfig

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    MapConfig.initConf('data/conf/simple.txt')
    pd = PointService(MapConfig.get())
    for p in pd.getTilePoints(6, 26, 36, 10):
        print p['id'], p['zpop']
    # for p in pd.getTilePoints(6, 27, 37, 1000):
    #     if p['id'] == '13616':
    #         print p['id']
    # builder = TopoJsonBuilder()
    # pd.addLayers(builder, 'gender', 6, 27, 36)
    # pd.addLayers(builder, 'gender', 6, 27, 37)
    # print builder.toJson()


