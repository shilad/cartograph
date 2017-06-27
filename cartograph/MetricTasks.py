import json
import os

import logging

import luigi

from cartograph import Config
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import MTimeMixin, TimestampedLocalTarget, ExternalFile
from cartograph.Utils import read_features

logger = logging.getLogger('cartograph.metric-tasks')

class MetricsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return TimestampedLocalTarget(__file__)

class AllMetrics(luigi.WrapperTask):
    def requires(self):
        config = Config.get()
        result = []
        metricDir = config.get('DEFAULT', 'metricDir')
        if not os.path.exists(metricDir):  # FIXME: Make sure this is the correct way to make sure MetricDir is created.
            os.makedirs(metricDir)
        for name in config.get('Metrics', 'active').split():
            metricConf = json.loads(config.get('Metrics', name))
            path = metricConf['path']
            args= {
                'name' : name,
                'inPath' : path,
                'outPath' : os.path.join(metricDir, name + '.json'),
            }
            result.append(MetricData(**args))
        return result

class MetricData(MTimeMixin, luigi.Task):
    name = luigi.Parameter()
    inPath = luigi.Parameter()
    outPath = luigi.Parameter()

    '''
    Creates a point layer for metric
    '''
    def output(self):
        return TimestampedLocalTarget(self.outPath)

    def requires(self):
        conf = Config.get()
        return (ExternalFile(self.inPath),
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
        externalData = read_features(self.inPath)

        print(points)
        print(externalData)

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

        print(len(records))

        for r in records:
            for sf in stringFields:
                r[sf] = str(r[sf])


        print(len(r))

        with open(self.outPath, "w") as f:
            for r in records:
                json.dump(r, f)
                f.write('\n')
