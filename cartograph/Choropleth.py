import json
import os
import shapely.geometry
from collections import defaultdict
import logging

import luigi
import geojson

from cartograph import Config
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import MTimeMixin, LoadGeoJsonTask, TimestampedLocalTarget, ExternalFile, LoadJsonTask
from cartograph.Utils import read_features

logger = logging.getLogger('cartograph.choropleth')

class ChoroplethCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return TimestampedLocalTarget(__file__)

class AllChoropleth(luigi.WrapperTask):
    def requires(self):
        config = Config.get()
        result = []
        gen = config.get('DEFAULT', 'generatedDir')
        for name in config.get('Metrics', 'active').split():
            jsStr = config.get('Metrics', name)
            metricConf = json.loads(jsStr)
            field = name
            path = metricConf['path']
            args= {
                '_name' : name,
                '_table' : 'choro' + name,
                '_inPath' : path,
                '_geoJsonPath' : os.path.join(gen, name + '.geojson'),
                '_jsonPath' : os.path.join(gen, name + '.json'),
            }
            result.append(ChoroplethLoader(**args))
            args['_table'] = name
            result.append(PointMetricLoader(**args))
        return result


class PointMetricLoader(LoadJsonTask):
    _name = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _geoJsonPath = luigi.Parameter()
    _jsonPath = luigi.Parameter()

    @property
    def table(self): return self._table

    @property
    def jsonPath(self): return self._jsonPath

    def requires(self):
        return (
            ChoroplethData(self._name, self._inPath, self._jsonPath, self._geoJsonPath)
        )

class ChoroplethLoader(LoadGeoJsonTask):
    _name = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _geoJsonPath = luigi.Parameter()
    _jsonPath = luigi.Parameter()

    @property
    def table(self): return self._table

    @property
    def geoJsonPath(self): return self._geoJsonPath

    def requires(self):
        return (
            ChoroplethData(self._name, self._inPath, self._jsonPath, self._geoJsonPath)
        )

class ChoroplethData(MTimeMixin, luigi.Task):
    name = luigi.Parameter()
    inpath = luigi.Parameter()
    jsonOut = luigi.Parameter()
    geoOut = luigi.Parameter()

    '''
    Creates a chloropleth layer
    '''
    def output(self):
        return TimestampedLocalTarget(self.jsonOut), TimestampedLocalTarget(self.geoOut)

    def requires(self):
        conf = Config.get()
        return (ExternalFile(self.inpath),
                ExternalFile(conf.get('ExternalFiles', 'external_ids')),
                CreateFullCoordinates(),
                ChoroplethCode())

    def run(self):
        config = Config.get()
        points = read_features(
            config.get('GeneratedFiles', 'article_coordinates'),
            config.get('ExternalFiles', 'external_ids'),
            required=('x', 'y', 'externalId')
        )
        externalData = read_features(self.inpath)

        mc = config.getint('MapConstants', 'max_coordinate') * 1.0
        mz = config.getint('MapConstants', 'max_zoom')

        cats = set()
        for d in externalData.values():
            cats.update(k for k in d if k != 'externalId')
        cats = list(cats)   # order them
        prior = { c : 1.0 for c in cats }
        qt = QuadTree(0, -mc, -mc, mc * 2.0, 10, mz, prior)

        with open(self.jsonOut, 'w') as f:
            for i, (id, p) in enumerate(points.items()):
                if i % 100000 == 0: logger.info('insert point %d of %d' % (i, len(points)))
                extId = p['externalId']
                if extId not in externalData: continue
                pinfo = { k : float(v) for (k, v) in externalData[extId].items() if k != 'id' }
                qt.insert(MetricPoint(id, float(p['x']), float(p['y']), pinfo))
                js = { c : pinfo.get(c, 0.0) for c in cats }
                js['id'] = id
                f.write(json.dumps(js) + '\n')

        feats = []
        for z in range(mz):
            logger.info("building choropleth regions for zoom %d", z)
            results = []
            qt.getAtDepth(z, results)
            logger.info("found %d regions", len(results))
            for r in results:
                points = [
                    (r.leftX, r.topY),
                    (r.leftX + r.size, r.topY),
                    (r.leftX + r.size, r.topY + r.size),
                    (r.leftX, r.topY + r.size),
                    (r.leftX, r.topY),
                ]
                geom = shapely.geometry.Polygon(points)
                props = { 'zoom' : z }
                for (k, v) in r.valueSums.items():
                    props[k] = v / r.numPoints
                for (k, v) in r.normalizedDist().items():
                    props['norm' + k] = v
                feats.append(
                    geojson.Feature(
                        geometry=geom,
                        properties=props
                    )
                )

        fc = geojson.FeatureCollection(feats)
        with open(self.geoOut, "w") as f:
            geojson.dump(fc, f)


class MetricPoint:
    def __init__(self, id, x, y, values):
        self.id = id
        self.x = x
        self.y = y
        self.values = values

    def __str__(self):
        return '{id=%s x=%.3f, y=%.3f, vals=%s}' % (self.id, self.x, self.y, self.values)

class QuadTree:
    def __init__(self, depth, leftX, topY, size, capacity, maxDepth, prior, numPriorPoints=1):
        self.depth = depth
        self.leftX = leftX
        self.topY = topY
        self.size = size
        self.capacity = capacity
        self.maxDepth = maxDepth
        self.prior = prior
        self.numPriorPoints = numPriorPoints

        self.numPoints = 0
        self.valueSums = defaultdict(float)
        t = 1.0 * sum(prior.values())
        self.normalizedSums = { k : (v * numPriorPoints / t) for (k, v) in prior.items() }

        self.children = []

        # For leaf nodes, this will be filled in...
        self.points = []

    def insert(self, mp):
        '''
        Inserts a metric point into the quadrant if the capacity of
        points per tile has not been reached. Adds the children
        of the tile into the quadtree structure and adds the
        point to the child tile if it contains the point.
        '''

        self.numPoints += 1

        t = sum(mp.values.values()) + sum(self.prior.values())
        for (k, v) in mp.values.items():
            self.valueSums[k] += v
            self.normalizedSums[k] += (v + self.prior[k]) / t
        self.points.append(mp)

        # are we a leaf that can accept the child?
        c = self.capacity
        if not self.children and (self.depth >= self.maxDepth or len(self.points) < c):
            return

        if not self.children:
            s = self.size / 2.0
            self.children.append(self.mkChild(self.leftX, self.topY))
            self.children.append(self.mkChild(self.leftX + s, self.topY))
            self.children.append(self.mkChild(self.leftX + s, self.topY + s))
            self.children.append(self.mkChild(self.leftX, self.topY + s))

        for p in self.points:
            for c in self.children:
                if c.contains(p.x, p.y):
                    c.insert(p)
                    break
            else:
                assert (False, '%s doesnt contain %s, %s' % (self, mp.x, mp.y))

        self.points = []

    def mkChild(self, x, y):
        return QuadTree(self.depth +1, x, y,
                self.size / 2.0, self.capacity, self.maxDepth,
                self.prior, self.numPriorPoints)

    def getAtDepth(self, depth, results):
        if self.depth == depth:
            results.append(self)
        else:
            for c in self.children:
                c.getAtDepth(depth, results)

    def normalizedDist(self):
        t = sum(self.normalizedSums.values())
        return { k : (v / t) for (k, v) in self.normalizedSums.items() }

    def contains(self, x, y):
        '''
        Determines if a point exists in a tile.
        '''
        return (x >= self.leftX and x <= self.leftX + self.size
                and y >= self.topY and y <= self.topY + self.size)

    def __repr__(self):
        return ('qt for (%.4f %.4f %.4f %.4f)'
                % (self.leftX, self.topY, self.leftX + self.size,
                   self.topY + self.size))