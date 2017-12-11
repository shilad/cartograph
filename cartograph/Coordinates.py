import logging
import random

import luigi
import numpy as np
from tsne import bh_sne
import pandas as pd
import filecmp

import FastKnn, Utils, MapConfig
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, getSampleIds
from PreReqs import WikiBrainNumbering
from PreReqs import SampleCreator
from AugmentMatrix import AugmentCluster

logger = logging.getLogger('cartograph.coordinates')


class CreateEmbedding(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes
    '''

    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.getSample("ExternalFiles",
                                                       "article_embedding"))

    def requires(self):
        config = MapConfig.get()
        return (
            WikiBrainNumbering(),
            AugmentCluster(),
            SampleCreator(config.get("GeneratedFiles", "vecs_with_labels_clusters"),
                          prereqs=[AugmentCluster()])
        )

    def run(self):
        config = MapConfig.get()
        # Create the embedding.
        featureDict = Utils.read_vectors(config.getSample("GeneratedFiles", "vecs_with_labels_clusters"))
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
        # result.sort_index(inplace=True)   # THIS BREAKS EVERYTHING. WHY?
        result.to_csv(config.getSample("ExternalFiles", "article_embedding"), sep='\t', index_label='index',
                      columns=['x', 'y'])


def test_CreateEmbedding_task():
    config = MapConfig.initTest()
    report = []
    # Create a unit test config object
    for i in range(3):
        testEmbed = CreateEmbedding()

        # Create the vectors sample
        testEmbed.requires()[-1].run()
        testEmbed.run()

        # For each point, count how many neighbors are retained in the embedding
        vecs = Utils.read_vectors(config.getSample("GeneratedFiles", "vecs_with_labels_clusters"))
        vecsdf = pd.read_table(config.getSample("GeneratedFiles", "vecs_with_labels_clusters"), skiprows=1,
                               skip_blank_lines=True,
                               header=None, index_col=0)
        points = pd.read_table(config.getSample("ExternalFiles", "article_embedding"), index_col='index')
        points.index = points.index.astype(str)

        features = pd.merge(vecs, points, how='inner', left_index=True, right_index=True)

        stat = []
        for i, (index, row) in enumerate(features.iterrows()):
            dist = vecsdf - row['vector']
            vectorDist = dist * dist
            vectorDist['distance'] = vectorDist.sum(axis=1)
            pointDist = ((row['x'] - features['x']) ** 2 + (row['y'] - features['y']) ** 2) ** 0.5
            vectorDist.sort_values('distance', inplace=True)
            pointDist.sort_values(inplace=True)
            vectorDist.index = vectorDist.index.astype(str)
            top10Vec = vectorDist.index[:10]  # 10 nearest neighbors of original vectors
            top10Point = pointDist.index[:10]  # 10 nearest neighbors of embedded points
            common = len(set(top10Vec).intersection(top10Point))  # Number of common neighbors
            stat.append(common)
        report.append(np.mean(stat))

    prob = np.mean(report)
    assert prob >= 4


class CreateFullAnnoyIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        config = MapConfig.get()
        super(CreateFullAnnoyIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.get("GeneratedFiles", "vecs_with_labels_clusters")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        return WikiBrainNumbering()

    def output(self):
        return TimestampedLocalTarget(self.knn.pathAnnoy), TimestampedLocalTarget(self.knn.pathIds)

    def run(self):
        self.knn.rebuild()


class CreateSampleAnnoyIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        config = MapConfig.get()
        super(CreateSampleAnnoyIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.getSample("GeneratedFiles", "vecs_with_labels_clusters")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        config = MapConfig.get()
        return WikiBrainNumbering(), SampleCreator(config.get("GeneratedFiles", "vecs_with_labels_clusters"))

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
        config = MapConfig.get()
        return TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                       "article_coordinates"))

    def requires(self):
        return CreateEmbedding()

    def run(self):
        config = MapConfig.get()

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

        points['x'] = X
        points['y'] = Y
        points.to_csv(config.getSample("GeneratedFiles", "article_coordinates"), sep='\t', index_label='index',
                      columns=['x', 'y'])


def test_createSample_task():
    config = MapConfig.initTest()

    # Create a unit test config object
    testSample = CreateSampleCoordinates()
    testSample.run()
    assert testSample is not None

    # All x,y coordinates <= config.getint("MapConstants", "max_coordinate")
    embedding = pd.read_table(config.getSample("GeneratedFiles", "article_coordinates"), index_col='index')
    maxCoor = config.getint("MapConstants", "max_coordinate")
    assert abs(embedding.all()).between(0, maxCoor).all()


class CreateFullCoordinates(MTimeMixin, luigi.Task):
    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "article_coordinates"))

    def requires(self):
        return CreateSampleCoordinates(), WikiBrainNumbering(), CreateSampleAnnoyIndex()

    def run(self):
        config = MapConfig.get()
        sampleCoords = pd.read_table(config.getSample("GeneratedFiles",
                                                      "article_coordinates"), index_col='index')
        sampleCoords.dropna(axis=0, how='any', inplace=True)
        sampleCoords.index = sampleCoords.index.astype(str)

        vecs = Utils.read_vectors(config.get("GeneratedFiles", "vecs_with_labels_clusters"))

        knn = FastKnn.FastKnn(config.getSample("GeneratedFiles", "vecs_with_labels_clusters"))
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
                logger.info('interpolating coordinates for point %s of %d' % (id, len(vecs)))
            if id in sampleCoords.index:
                x = float(sampleCoords.ix[id, 'x'])
                y = float(sampleCoords.ix[id, 'y'])
            else:
                if len(row['vector']) == 0: continue
                centroids = []
                for id2, score in knn.neighbors(row['vector'], 10):
                    # if id2.isdigit():
                    # id2 = int(id2)
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
    config = MapConfig.initTest()

    knn = FastKnn.FastKnn(config.getSample("GeneratedFiles", "vecs_with_labels_clusters"))
    knn.rebuild()

    # Create a unit test config object
    testCoor = CreateFullCoordinates()
    testCoor.run()
    assert testCoor is not None

    # Coordinates within Max_Coordinates
    embedding = pd.read_table(config.get("GeneratedFiles", "article_coordinates"), index_col='index')
    maxCoor = config.getint("MapConstants", "max_coordinate")
    assert abs(embedding.all()).between(0, maxCoor).all()

    # Neighbors are preserved
    vecs = Utils.read_vectors(config.get("GeneratedFiles", "vecs_with_labels_clusters"))  # Each entry of vectors in a column
    vecsdf = pd.read_table(config.get("GeneratedFiles", "vecs_with_labels_clusters"), skiprows=1,
                           skip_blank_lines=True,
                           header=None, index_col=0)  # Vectors are merged in one column
    embedding.index = embedding.index.astype(str)

    features = pd.merge(vecs, embedding, how='inner', left_index=True, right_index=True)

    stat = []
    for i, (index, row) in enumerate(features.iterrows()):
        dist = vecsdf - row['vector']
        vectorDist = dist * dist
        vectorDist['distance'] = vectorDist.sum(axis=1)
        pointDist = ((row['x'] - features['x']) ** 2 + (row['y'] - features['y']) ** 2) ** 0.5
        vectorDist.sort_values('distance', inplace=True)
        pointDist.sort_values(inplace=True)
        vectorDist.index = vectorDist.index.astype(str)
        top10Vec = vectorDist.index[:10]  # 10 nearest neighbors of original vectors
        top10Point = pointDist.index[:10]  # 10 nearest neighbors of embedded points
        common = len(set(top10Vec).intersection(top10Point))  # Number of common neighbors
        stat.append(common)
    assert np.mean(stat) >= 3

    # Points are not on top of each other
    uniqueX = np.unique(embedding.as_matrix(['x']).round(5))
    uniqueY = np.unique(embedding.as_matrix(['y']).round(5))
    assert len(uniqueX) == len(embedding['x'])
    assert len(uniqueY) == len(embedding['y'])
