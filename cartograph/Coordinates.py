import logging
import luigi
import numpy as np
from tsne import bh_sne

import FastKnn, Utils, Config
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, getSampleIds
from PreReqs import WikiBrainNumbering
from cartograph.Popularity import SampleCreator

logger = logging.getLogger('cartograph.coordinates')


class CreateEmbedding(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes
    '''
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.getSample("ExternalFiles",
                                            "article_embedding"))

    def requires(self):
        config = Config.get()
        return (
            WikiBrainNumbering(),
            SampleCreator(config.get("ExternalFiles", "vecs_with_id"))
        )

    def run(self):
        config = Config.get()
        # Create the embedding.
        featureDict = Utils.read_features(config.getSample("ExternalFiles",
                                                          "vecs_with_id"),
                                          id_set=getSampleIds())
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        out = bh_sne(vectors,
                     pca_d=None,
                     theta=config.getfloat("PreprocessingConstants", "tsne_theta"))
        X, Y = list(out[:, 0]), list(out[:, 1])
        Utils.write_tsv(config.getSample("ExternalFiles", "article_embedding"),
                        ("index", "x", "y"), keys, X, Y)


class CreateFullAnnoyIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        config = Config.get()
        super(CreateFullAnnoyIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.get("ExternalFiles", "vecs_with_id")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        return WikiBrainNumbering()

    def output(self):
        return TimestampedLocalTarget(self.knn.pathAnnoy), TimestampedLocalTarget(self.knn.pathIds)

    def run(self):
        self.knn.rebuild()


class CreateSampleAnnoyIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        config = Config.get()
        super(CreateSampleAnnoyIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.getSample("ExternalFiles", "vecs_with_id")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        config = Config.get()
        return WikiBrainNumbering(), SampleCreator(config.get("ExternalFiles", "vecs_with_id"))

    def output(self):
        return TimestampedLocalTarget(self.knn.pathAnnoy), TimestampedLocalTarget(self.knn.pathIds)

    def run(self):
        self.knn.rebuild()


class CreateSampleCoordinates(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes.
    '''
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                            "article_coordinates"))

    def requires(self):
        return CreateEmbedding(), CreateSampleAnnoyIndex()

    def run(self):
        config = Config.get()

        # Rescale sampled embedded points
        points = Utils.read_features(config.getSample("ExternalFiles",
                                               "article_embedding"))
        keys = list(points.keys())
        X = [float(points[k]['x']) for k in keys]
        Y = [float(points[k]['y']) for k in keys]
        maxVal = max(abs(v) for v in X + Y)
        scaling = config.getint("MapConstants", "max_coordinate") / maxVal
        X = [x * scaling for x in X]
        Y = [y * scaling for y in Y]

        Utils.write_tsv(config.getSample("GeneratedFiles",
                                  "article_coordinates"),
                        ("index", "x", "y"), keys, X, Y)


class CreateFullCoordinates(MTimeMixin, luigi.Task):
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "article_coordinates"))

    def requires(self):
        return CreateSampleCoordinates(), WikiBrainNumbering(), CreateSampleAnnoyIndex()

    def run(self):
        config = Config.get()
        sampleCoords = Utils.read_features(config.getSample("GeneratedFiles", "article_coordinates"))
        vecs = Utils.read_features(config.get("ExternalFiles", "vecs_with_id"))
        knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
        assert(knn.exists())
        knn.read()
        ids = []
        X = []
        Y = []
        for i, (id, row) in enumerate(vecs.items()):
            if i % 10000 == 0:
                logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
            xSums = 0.0
            ySums = 0.0
            scoreSums = 0.0
            if len(row['vector']) == 0: continue
            hood = knn.neighbors(row['vector'], 5)
            for (id2, score) in hood:
                xSums += score * float(sampleCoords[id2]['x'])
                ySums += score * float(sampleCoords[id2]['y'])
                scoreSums += score
            X.append(xSums / scoreSums)
            Y.append(ySums / scoreSums)
            ids.append(id)

        Utils.write_tsv(config.get("GeneratedFiles",
                                  "article_coordinates"),
                        ("index", "x", "y"), ids, X, Y)