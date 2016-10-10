import logging
import random

import luigi
import numpy as np
from tsne import bh_sne

import FastKnn, Utils, Config
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, getSampleIds
from PreReqs import WikiBrainNumbering
from cartograph.PreReqs import SampleCreator

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
            SampleCreator(config.get("ExternalFiles", "best_vecs_with_id"))
        )

    def run(self):
        config = Config.get()
        # Create the embedding.
        featureDict = Utils.read_features(config.getSample("ExternalFiles",
                                                          "best_vecs_with_id"),
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
        return CreateEmbedding()

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
        sampleCoords = Utils.read_features(config.getSample("GeneratedFiles", "article_coordinates"),
                                           required=('x', 'y'))
        vecs = Utils.read_features(config.get("ExternalFiles", "vecs_with_id"))
        knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
        assert(knn.exists())
        knn.read()
        ids = []
        X = []
        Y = []

        def dist2(x0, y0, x1, y1):
            dx = x0 - x1
            dy = y0 - y1
            return (dx * dx + dy * dy) ** 0.5

        threshold = config.getfloat('MapConstants', 'max_coordinate') / 100.0
        noise = threshold / 10.0    # for points with only one surrogate, add this much random noise

        for i, (id, row) in enumerate(vecs.items()):
            if i % 10000 == 0:
                logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
            if id in sampleCoords:
                x = float(sampleCoords[id]['x'])
                y = float(sampleCoords[id]['y'])
            else:
                if len(row['vector']) == 0: continue
                centroids = []
                for id2, score in knn.neighbors(row['vector'], 10):
                    if id2 not in sampleCoords: continue
                    x = float(sampleCoords[id2]['x'])
                    y = float(sampleCoords[id2]['y'])
                    if score >= 0.0:
                        closestIndex = -1
                        closestDist = 1000000000000
                        for i, (s, n, xs, ys) in enumerate(centroids):
                            d = dist2(x, y, xs / s, ys / s)
                            if d < closestDist:
                                closestDist = d
                                closestIndex = i
                        if closestDist < threshold:
                            centroids[closestIndex][0] += score
                            centroids[closestIndex][1] += 1
                            centroids[closestIndex][2] += x * score
                            centroids[closestIndex][3] += y * score
                        else:
                            centroids.append([score, 1, x * score, y * score])

                if not centroids: continue

                sumScores, n, sumXs, sumYs = sorted(centroids, reverse=True)[0]

                if sumScores == 0.0: continue

                x = sumXs / sumScores
                y = sumYs / sumScores

                # make sure points aren't right on top of each other!
                if n == 1:
                    x += random.uniform(-noise, +noise)
                    y += random.uniform(-noise, +noise)

            X.append(x)
            Y.append(y)
            ids.append(id)

        Utils.write_tsv(config.get("GeneratedFiles",
                                  "article_coordinates"),
                        ("index", "x", "y"), ids, X, Y)
