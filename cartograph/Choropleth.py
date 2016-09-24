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
            jsStr = config.get('Metrics', name)
            metricConf = json.loads(jsStr)
            path = metricConf['path']
            args= {
                '_name' : name,
                '_fields' : metricConf['fields'],
                '_colors' : metricConf['colors'],
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

class StyleWriter(luigi.Task):
    _name = luigi.Parameter()
    _fields = luigi.Parameter()
    _colors = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _outPath = luigi.Parameter()
    _xmlPath = luigi.Parameter()

    def run(self):
        conf = Config.get()
        m = MapnikHelper()

        nLevels = 3
        styleNames = []
        for color, field in zip(self._colors.split(), self._fields.split()):
            for i in range(nLevels):
                name = "%s_%s_%d" % (self._name, field, i)
                styleNames.append(name)
                style = m.mkStyle(name)
                start = 1.0 / len(self._colors.split())
                step = (1.0 - start) / nLevels
                r = ET.SubElement(style, 'Rule')
                f = ET.SubElement(r, 'Filter').text = (
                    '[smoothed%s] >= %.3f and [smoothed%s] < %.3f' %
                    (field, start + step * i, field, start + step * (i + 1))
                )
                ms = ET.SubElement(r, "MarkersSymbolizer")
                ms.set('allow-overlap', 'true')
                ms.set('fill', color)
                ms.set('stroke', color)
                ms.set('opacity', str(0.2 * i))
                ms.set('width', '4')
                ms.set('height', '4')
                ms.set('stroke-width', '2')
                ms.set('stroke-opacity', str(0.1 * i))
                ms.set('placement', 'point')
                ms.set('marker-type', 'ellipse')
                ms.set('comp-op', 'multiply')

        layer = m.mkPGLayer(conf, self._name, self._table, styleNames)

        m.write(self._xmlPath)

    def output(self):
        return TimestampedLocalTarget(self._xmlPath)

    def requires(self):
        return (
            ChoroplethGeoJsonLoader(self._name, self._table, self._inPath, self._outPath)
        )

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
        return (
            ChoroplethData(self._name, self._inPath, self._outPath)
        )

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
                CreateFullCoordinates())
                # ChoroplethCode())

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
