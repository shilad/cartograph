import json
import os

import shapely.geometry
import logging

import luigi
import geojson

from cartograph import Config
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import MTimeMixin, LoadGeoJsonTask, TimestampedLocalTarget, ExternalFile, LoadJsonTask
from cartograph.Utils import read_features

logger = logging.getLogger('cartograph.choropleth')

class MetricsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return TimestampedLocalTarget(__file__)

class AllMetrics(luigi.WrapperTask):
    def requires(self):
        config = Config.get()
        result = []
        metricDir = config.get('DEFAULT', 'metricDir')
        for name in config.get('Metrics', 'active').split():
            metricConf = json.loads(config.get('Metrics', name))
            path = metricConf['path']
            args= {
                '_name' : name,
                '_table' : name,
                '_inPath' : path,
                '_outPath' : os.path.join(metricDir, name + '.json'),
            }
            result.append(MetricJsonLoader(**args))
        return result

class MetricJsonLoader(LoadJsonTask):
    _name = luigi.Parameter()
    _table = luigi.Parameter()
    _inPath = luigi.Parameter()
    _outPath = luigi.Parameter()

    @property
    def table(self): return self._table

    @property
    def jsonPath(self): return self._outPath

    def requires(self):
        return MetricData(self._name, self._inPath, self._outPath)

class MetricData(MTimeMixin, luigi.Task):
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
                MetricsCode())

    def run(self):
        config = Config.get()
        points = read_features(
            config.get('GeneratedFiles', 'article_coordinates'),
            config.get('ExternalFiles', 'external_ids'),
            required=('x', 'y', 'externalId')
        )
        externalData = read_features(self.inpath)

        records = []
        stringFields = set()

        for i, (id, p) in enumerate(points.items()):
            if i % 100000 == 0: logger.info('insert point %d of %d' % (i, len(points)))
            extId = p['externalId']
            if extId not in externalData: continue
            pinfo = { 'id' : id }
            for (k, v) in externalData[extId].items():
                try:
                    v = float(v)
                except ValueError:
                    stringFields.add(k)
                pinfo[k] = v
            records.append(pinfo)

        for r in records:
            for sf in stringFields:
                r[sf] = str(r[sf])

        with open(self.outPath, "w") as f:
            for r in records:
                json.dump(r, f)
                f.write('\n')
