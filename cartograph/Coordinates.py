import logging
import random

import luigi
import numpy as np
from tsne import bh_sne
import pandas as pd
import filecmp

import FastKnn, Utils, Config
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, getSampleIds
from PreReqs import WikiBrainNumbering
from PreReqs import SampleCreator

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
        # config = Config.get()
        # # Create the embedding.
        # featureDict = Utils.read_features(config.getSample("ExternalFiles",
        #                                                    "best_vecs_with_id"),
        #                                   id_set=getSampleIds())
        # keys = list(featureDict.keys())
        # vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        # out = bh_sne(vectors,
        #              pca_d=None,
        #              perplexity=config.getfloat("PreprocessingConstants", "tsne_perplexity"),
        #              theta=config.getfloat("PreprocessingConstants", "tsne_theta"))
        # X, Y = list(out[:, 0]), list(out[:, 1])
        # Utils.write_tsv(config.getSample("ExternalFiles", "article_embedding"),
        #                 ("index", "x", "y"), keys, X, Y)

        config = Config.get()
        # Create the embedding.
        featureDict = Utils.read_vectors(config.getSample("ExternalFiles", "best_vecs_with_id"))
        sampleIds = getSampleIds()
        featureDict = featureDict.loc[featureDict.index.isin(sampleIds)]

        vectors = [list(i) for i in featureDict['vector']]
        vectors = np.array(vectors)

        out = bh_sne(vectors,
                     pca_d=None,
                     perplexity=config.getfloat("PreprocessingConstants", "tsne_perplexity"),
                     theta=config.getfloat("PreprocessingConstants", "tsne_theta"))
        X, Y = list(out[:, 0]), list(out[:, 1])

        data = {'index': featureDict.index, 'x': X, 'y': Y}
        result = pd.DataFrame(data, columns=['index', 'x', 'y'])
        result.set_index('index', inplace=True)
        # result.sort_index(inplace=True)   THIS BREAKS EVERYTHING. WHY?
        result.to_csv(config.getSample("ExternalFiles", "article_embedding"), sep='\t', index_label='index',
                      columns=['x', 'y'])
#
def test_CreateEmbedding_task():
    config = Config.initTest()

    # Create a unit test config object
    testEmbed = CreateEmbedding()

    # Create the vectors sample
    testEmbed.requires()[-1].run()
    testEmbed.run()

    # For each point, count how many neighbors are retained in the embedding
    vecs = Utils.read_vectors(config.getSample("ExternalFiles", "best_vecs_with_id"))
    points = pd.read_table(config.getSample("ExternalFiles", "article_embedding"))
    points.index = points.index.astype(str)


    features = pd.merge(vecs, points, how='inner',
                        left_index=True, right_index=True)

    for index, row in features.iterrows():
        vectorDist = (features['vector'].dot(row['vector']))
        pointDist = ((row['x'] - features['x']) ** 2 + (row['y'] - features['y']) ** 2) ** 0.5
        print(vectorDist.shape, pointDist.shape)







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
        # points = Utils.read_features(config.getSample("ExternalFiles",
        #                                        "article_embedding"))
        # keys = list(points.keys())
        # X = [float(points[k]['x']) for k in keys]
        # Y = [float(points[k]['y']) for k in keys]
        # maxVal = max(abs(v) for v in X + Y)
        # scaling = config.getint("MapConstants", "max_coordinate") / maxVal
        # X = [x * scaling for x in X]
        # Y = [y * scaling for y in Y]
        #
        # Utils.write_tsv(config.getSample("GeneratedFiles",
        #                           "article_coordinates"),
        #                 ("index", "x", "y"), keys, X, Y)

        config = Config.get()

        # Rescale sampled embedded points
        points = pd.read_table(config.getSample("ExternalFiles",
                                                "article_embedding"), index_col='index')
        points.sort_index(inplace=True)
        X = pd.np.array(points['x'])
        Y = pd.np.array(points['y'])
        maxVal = max(abs(np.append(X, Y)))

        scaling = config.getint("MapConstants", "max_coordinate") / maxVal
        X = [x * scaling for x in X]
        Y = [y * scaling for y in Y]

        # Utils.write_tsv(config.getSample("GeneratedFiles",
        #                                  "article_coordinates"),
        #                 ("index", "x", "y"), points.index, X, Y)
        points['x'] = X
        points['y'] = Y
        points.to_csv(config.getSample("GeneratedFiles", "article_coordinates"), sep='\t', index_label='index',
                      columns=['x', 'y'])


def test_createSample_task():
    config = Config.initTest()

    # Create a unit test config object
    testSample = CreateSampleCoordinates()
    testSample.run()
    assert testSample is not None

    result = pd.read_table(config.getSample("GeneratedFiles", "article_coordinates"), index_col='index')
    correct = pd.read_table('./data/test/tsv/coordinates.sample_50_correct.tsv', index_col='index')

    tol = 0.01
    for (id1, row1), (id2, row2) in zip(correct.iterrows(), result.iterrows()):
        assert id1 == id2
        assert abs(row1['x'] - row2['x']) < tol
        assert abs(row1['y'] - row2['y']) < tol


class CreateFullCoordinates(MTimeMixin, luigi.Task):
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "article_coordinates"))

    def requires(self):
        return CreateSampleCoordinates(), WikiBrainNumbering(), CreateSampleAnnoyIndex()

    def run(self):
        # config = Config.get()
        # sampleCoords = Utils.read_features(config.getSample("GeneratedFiles", "article_coordinates"),
        #                                    required=('x', 'y'))
        # vecs = Utils.read_features(config.get("ExternalFiles", "vecs_with_id"))
        # knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
        # assert (knn.exists())
        # knn.read()
        # ids = []
        # X = []
        # Y = []
        #
        # def dist2(x0, y0, x1, y1):
        #     dx = x0 - x1
        #     dy = y0 - y1
        #     return (dx * dx + dy * dy) ** 0.5
        #
        # threshold = config.getfloat('MapConstants', 'max_coordinate') / 100.0
        # noise = threshold / 10.0  # for points with only one surrogate, add this much random noise
        #
        # for i, (id, row) in enumerate(vecs.items()):
        #     if i % 10000 == 0:
        #         logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
        #     if id in sampleCoords:
        #         x = float(sampleCoords[id]['x'])
        #         y = float(sampleCoords[id]['y'])
        #     else:
        #         if len(row['vector']) == 0: continue
        #         centroids = []
        #         for id2, score in knn.neighbors(row['vector'], 10):
        #             if id2 not in sampleCoords: continue
        #             x = float(sampleCoords[id2]['x'])
        #             y = float(sampleCoords[id2]['y'])
        #             if score >= 0.0:
        #                 closestIndex = -1
        #                 closestDist = 1000000000000
        #                 for i, (s, n, xs, ys) in enumerate(centroids):
        #                     d = dist2(x, y, xs / s, ys / s)
        #                     if d < closestDist:
        #                         closestDist = d
        #                         closestIndex = i
        #                 if closestDist < threshold:
        #                     centroids[closestIndex][0] += score
        #                     centroids[closestIndex][1] += 1
        #                     centroids[closestIndex][2] += x * score
        #                     centroids[closestIndex][3] += y * score
        #                 else:
        #                     centroids.append([score, 1, x * score, y * score])
        #
        #         if not centroids: continue
        #
        #         sumScores, n, sumXs, sumYs = sorted(centroids, reverse=True)[0]
        #
        #         if sumScores == 0.0: continue
        #
        #         x = sumXs / sumScores
        #         y = sumYs / sumScores
        #
        #         # make sure points aren't right on top of each other!
        #         if n == 1:
        #             x += random.uniform(-noise, +noise)
        #             y += random.uniform(-noise, +noise)
        #
        #     X.append(x)
        #     Y.append(y)
        #     ids.append(id)
        #
        # Utils.write_tsv(config.get("GeneratedFiles",
        #                            "article_coordinates"),
        #                 ("index", "x", "y"), ids, X, Y)

        config = Config.get()

        sampleCoords = pd.read_table(config.getSample("GeneratedFiles",
                                                      "article_coordinates"), index_col='index')
        sampleCoords.dropna(axis=0, how='any', inplace=True)

        vecs = pd.read_table(config.get("ExternalFiles", "vecs_with_id"), skip_blank_lines=True, skiprows=1,
                             header=None)
        vecs['vectorTemp'] = vecs.iloc[:, 1:].apply(lambda x: tuple(x),
                                                    axis=1)  # join all vector columns into same column as a tuplevecs['vector'] = vecs['vector'].tolist()
        vecs.drop(vecs.columns[1:-1], axis=1, inplace=True)  # drop all columns but the index and the vectorTemp column
        vecs.columns = ['index', 'vector']  # print type(vecs['vector'])
        vecs = vecs.set_index('index')

        knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
        assert (knn.exists())
        knn.read()

        ids = []
        X = []
        Y = []

        def dist2(x0, y0, x1, y1):
            dx = x0 - x1
            dy = y0 - y1
            return (dx * dx + dy * dy) ** 0.5

        threshold = config.getfloat('MapConstants', 'max_coordinate') / 100.0
        noise = threshold / 10.0  # for points with only one surrogate, add this much random noise

        j = 0  # For logging
        for id, row in vecs.iterrows():
            if j % 10000 == 0:
                logger.info('interpolating coordinates for point %d of %d' % (id, len(vecs)))
            if id in sampleCoords.index:
                x = float(sampleCoords.ix[id, 'x'])
                y = float(sampleCoords.ix[id, 'y'])
            else:
                if len(row['vector']) == 0: continue
                centroids = []
                for id2, score in knn.neighbors(row['vector'], 10):
                    if id2.isdigit():
                        id2 = int(id2)
                        if id2 not in sampleCoords.index: continue
                        x = float(sampleCoords.ix[id2, 'x'])
                        y = float(sampleCoords.ix[id2, 'y'])
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
            j += 1

        result = pd.DataFrame()
        result['x'] = X
        result['y'] = Y
        result['index'] = ids

        result.set_index('index', inplace=True)
        result.to_csv(config.get("GeneratedFiles", "article_coordinates"), sep='\t', index_label='index',
                      columns=['x', 'y'])


def test_createCoordinates_task():
    config = Config.initTest()

    knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
    knn.rebuild()

    # Create a unit test config object
    testCoor = CreateFullCoordinates()
    testCoor.run()
    assert testCoor is not None

    correct = pd.read_table('./data/test/tsv/coordinates_50_correct.tsv', index_col='index')
    correct.sort_index(inplace=True)
    correct.to_csv('./data/test/tsv/coordinates_50_correct.tsv', sep='\t', index_label='index',
                  columns=['x', 'y'])
    result = pd.read_table('./data/test/tsv/coordinates.tsv', index_col='index')

    tol = 0.1
    for (id1, row1), (id2, row2) in zip(correct.iterrows(), result.iterrows()):
        assert id1 == id2
        assert abs(row1['x'] - row2['x']) < tol
        assert abs(row1['y'] - row2['y']) < tol
