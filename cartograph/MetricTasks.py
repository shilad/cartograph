import json
import os

import logging

import luigi

from cartograph import MapConfig
from cartograph.Regions import MakeRegions
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import MTimeMixin, TimestampedLocalTarget, ExternalFile
from cartograph.Utils import read_features

logger = logging.getLogger('cartograph.metric-tasks')

class MetricsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return TimestampedLocalTarget(__file__)


class AllMetrics(MTimeMixin, luigi.Task):

    '''
    Creates a point layer for metric
    '''
    def output(self):
        return TimestampedLocalTarget(self.getOutputPath())

    def requires(self):
        conf = MapConfig.get()
        return (ExternalFile(conf.get('Metrics', 'path')),
                ExternalFile(conf.get('ExternalFiles', 'external_ids')),
                CreateFullCoordinates(),
                MakeRegions(),
                MetricsCode())

    def getOutputPath(self):
        conf = MapConfig.get()
        return os.path.join(conf.get('DEFAULT', 'metricDir'), 'metrics.json')


    def run(self):
        # TODO: Make sure we fold in cluster ids.
        config = MapConfig.get()
        points = read_features(
            config.get('GeneratedFiles', 'article_coordinates'),
            config.get('ExternalFiles', 'external_ids'),
            config.get("GeneratedFiles", "clusters_with_id"),
            required=('x', 'y', 'cluster')
        )
        metrics = read_features(config.get('Metrics', 'path'))

        records = []

        for i, (id, p) in enumerate(points.items()):
            if i % 100000 == 0: logger.info('insert point %d of %d' % (i, len(points)))
            pinfo = { 'id' : id, 'Cluster' :  p['cluster']}
            if id not in metrics: continue
            pinfo.update(metrics[id])
            records.append(pinfo)

        with open(self.getOutputPath(), "w") as f:
            for r in records:
                json.dump(r, f)
                f.write('\n')
