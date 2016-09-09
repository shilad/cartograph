import os

import luigi

from cartograph import Config
from cartograph.LuigiUtils import TimestampedLocalTarget, MTimeMixin, getSampleIds


class LabelNames(luigi.Task):
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''
    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "region_names")))

    def run(self):
        config = Config.get()

        with open(config.get("ExternalFiles", "region_names"), 'w') as f:
            f.write('cluster_id\tlabel\n')
            numClusters = config.getint('PreprocessingConstants', 'num_clusters')
            for i in range(numClusters + 1): # +1 is for water cluster
                f.write('%d\tCluster %d\n' % (i, i))
            f.close()

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


class SampleCreator(MTimeMixin, luigi.Task):
    path = luigi.Parameter()

    def requires(self):
        return (
            WikiBrainNumbering(),
            ArticlePopularity(),
            EnsureDirectoriesExist()
        )

    def samplePath(self):

        config = Config.get()
        n = config.getint('PreprocessingConstants', 'sample_size')
        return Config.samplePath(self.path, n)

    def output(self):
        return TimestampedLocalTarget(self.samplePath())

    def run(self):
        sampleIds = getSampleIds()
        with open(self.path, 'r') as input, open(self.samplePath(), 'w') as output:
            header = input.readline()
            output.write(header + '\n')
            for line in input:
                id = line.split('\t')[0]
                if id in sampleIds:
                    output.write(line + '\n')