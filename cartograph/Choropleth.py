import json
import os

from lxml import etree as ET


import shapely.geometry
import logging

import luigi
import geojson

from cartograph import Config
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import MTimeMixin, LoadGeoJsonTask, TimestampedLocalTarget, ExternalFile, LoadJsonTask
from cartograph.MapnikHelper import MapnikHelper
from cartograph.NormalizedMultinomialMetric import NormalizedMultinomialMetric
from cartograph.Utils import read_features

logger = logging.getLogger('cartograph.choropleth')

class ChoroplethCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return TimestampedLocalTarget(__file__)

class AllChoropleth(luigi.WrapperTask):
    def requires(self):
        config = Config.get()
        result = []
        geoDir = config.get('DEFAULT', 'geojsonDir')
        mapDir = config.get('DEFAULT', 'mapDir')
        for name in config.get('Metrics', 'active').split():
            metricConf = json.loads(config.get('Metrics', name))
            path = metricConf['path']
            args= {
                '_name' : name,
                '_fields' : ' '.join(metricConf['fields']),
                '_colors' : ' '.join(metricConf['colors']),
                '_bins' : metricConf['bins'],
                '_table' : name,
                '_inPath' : path,
                '_outPath' : os.path.join(geoDir, name + '.geojson'),
                '_xmlPath' : os.path.join(mapDir, name + '_only.xml'),
            }
            result.append(StyleWriter(**args))
        return result

class MapRenderer(luigi.Task):
    _name = luigi.Parameter()
    _fields = luigi.Parameter()
    _colors = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _outPath = luigi.Parameter()
    _xmlPath = luigi.Parameter()

    pass

class StyleWriter(MTimeMixin, luigi.Task):
    _name = luigi.Parameter()
    _fields = luigi.Parameter()
    _colors = luigi.Parameter()
    _bins = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _outPath = luigi.Parameter()
    _xmlPath = luigi.Parameter()

    def run(self):
        conf = Config.get()
        m = MapnikHelper()

        nLevels = self._bins
        styleNames = []
        fields = self._fields.split()
        colors = self._colors.split()
        metric = NormalizedMultinomialMetric(fields, nLevels)
        for color, field in zip(colors, fields):
            for i in range(1, nLevels+1):
                name = "%s_%s_%d" % (self._name, field, i)
                styleNames.append(name)
                start = metric.getMinThreshold(i)
                stop = metric.getMinThreshold(i + 1)
                style = m.mkStyle(name)
                style.set('comp-op', 'multiply')
                r = ET.SubElement(style, 'Rule')
                f = ET.SubElement(r, 'Filter').text = (
                    '[smoothed%s] > %.3f and [smoothed%s] <= %.3f' %
                    (field, start, field, stop)
                )
                ms = ET.SubElement(r, "MarkersSymbolizer")
                ms.set('allow-overlap', 'true')
                ms.set('fill', color)
                ms.set('stroke', color)
                ms.set('opacity', str(0.4 * i / nLevels))
                ms.set('width', '6')
                ms.set('height', '6')
                ms.set('stroke-width', '0')
                ms.set('placement', 'point')
                ms.set('marker-type', 'ellipse')
                ms.set('comp-op', 'multiply')

        layer = m.mkPGLayer(conf, self._name, self._table, styleNames)

        m.write(self._xmlPath)

    def output(self):
        return TimestampedLocalTarget(self._xmlPath)

    def requires(self):
        return ChoroplethGeoJsonLoader(self._name, self._table, self._inPath, self._outPath)

class ChoroplethGeoJsonLoader(LoadGeoJsonTask):
    _name = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _outPath = luigi.Parameter()

    @property
    def table(self): return self._table

    @property
    def geoJsonPath(self): return self._outPath

    def requires(self):
        return ChoroplethData(self._name, self._inPath, self._outPath)

class ChoroplethData(MTimeMixin, luigi.Task):
    name = luigi.Parameter()
    inpath = luigi.Parameter()
    outPath = luigi.Parameter()

    '''
    Creates a point layer for metric
    '''
    def output(self):
        return TimestampedLocalTarget(self.outPath)

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

        feats = []

        for i, (id, p) in enumerate(points.items()):
            if i % 100000 == 0: logger.info('insert point %d of %d' % (i, len(points)))
            extId = p['externalId']
            if extId not in externalData: continue
            pinfo = { k : float(v) for (k, v) in externalData[extId].items() }
            total = sum(pinfo.values()) + len(pinfo)
            for (k, v) in pinfo.items():
                pinfo['smoothed' + k] = (v + 1.0) / total
            pinfo['id'] = id
            geom = shapely.geometry.Point(float(p['x']), float(p['y']))
            feats.append(
                geojson.Feature(
                    geometry=geom,
                    properties=pinfo
                )
            )

        fc = geojson.FeatureCollection(feats)
        with open(self.outPath, "w") as f:
            geojson.dump(fc, f)
