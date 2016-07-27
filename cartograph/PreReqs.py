import os

import luigi

from cartograph import Config
from cartograph.LuigiUtils import TimestampedLocalTarget, MTimeMixin


class LabelNames(luigi.ExternalTask):
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''
    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "region_names")))

    def requires(self):
        return EnsureDirectoriesExist() # This should occur in at least one of the sample tasks


class ArticlePopularity(luigi.ExternalTask):
    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "popularity")))


class WikiBrainNumbering(MTimeMixin, luigi.ExternalTask):
    '''
    Number the name and vector output of WikiBrain files so that each
    article has a unique id corrosponding to all of its data for future
    use of any subset of features of interest
    '''

    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles",
                                             "vecs_with_id")),
                TimestampedLocalTarget(config.get("ExternalFiles",
                                             "names_with_id")))


class EnsureDirectoriesExist(luigi.Task):
    def __init__(self, *args, **kwargs):
        super(EnsureDirectoriesExist, self).__init__(*args, **kwargs)
        self.configKeys = ('baseDir', 'externalDir', 'generatedDir', 'geojsonDir', 'mapDir')

    def output(self):
        config = Config.get()
        return list(
            luigi.LocalTarget(config.get('DEFAULT', n)) for n in self.configKeys
        )

    def requires(self): return []

    def run(self):
        config = Config.get()
        for k in self.configKeys:
            fn = config.get('DEFAULT', k)
            if not os.path.isdir(fn): os.makedirs(fn)