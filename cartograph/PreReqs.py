import os

import luigi
from cartograph import Config
from cartograph.LuigiUtils import TimestampedLocalTarget, MTimeMixin, getSampleIds


class ArticlePopularity(luigi.ExternalTask):
    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "popularity")))


class Word2VecFile(luigi.ExternalTask):
    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "w2v")))


class ExternalIdFile(luigi.ExternalTask):
    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "external_ids")))


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
        self.configKeys = ('baseDir', 'externalDir', 'generatedDir', 'geojsonDir', 'mapDir', 'metricDir')

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
            EnsureDirectoriesExist(),
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