import luigi

from cartograph import PreReqs
from cartograph import Config
from cartograph import Utils
from cartograph.LuigiUtils import MTimeMixin, TimestampedLocalTarget, getSampleIds


class PopularityIdentifier(MTimeMixin, luigi.Task):
    '''
    Generate a tsv that matches Wikibrain popularity count to a unique
    article ID for later compatibility with Util.read_features()
    '''
    def requires(self):
        return (PreReqs.WikiBrainNumbering(),
                PreReqs.ArticlePopularity())

    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("GeneratedFiles",
                                                 "popularity_with_id")))

    def run(self):
        config = Config.get()
        featureDict = Utils.read_features(config.get("ExternalFiles",
                                                    "names_with_id"))
        idList = list(featureDict.keys())

        nameDict = {}
        with open(config.get("ExternalFiles", "popularity")) as popularity:
            lines = popularity.readlines()
            for line in lines:
                lineAr = line.split("\t")
                name = lineAr[0]
                pop = lineAr[1][:-1]
                nameDict[name] = pop

        popularityList = []
        for featureID in idList:
            name = featureDict[featureID]["name"]
            popularityList.append(nameDict[name])

        Utils.write_tsv(config.get('GeneratedFiles', 'popularity_with_id'),
                        ("id", "popularity"),
                        idList, popularityList)


class SampleCreator(MTimeMixin, luigi.Task):
    path = luigi.Parameter()

    def requires(self):
        return (
            PreReqs.WikiBrainNumbering(),
            PopularityIdentifier(),
            PreReqs.EnsureDirectoriesExist()
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

