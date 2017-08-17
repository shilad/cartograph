import luigi
import MapConfig
import Utils
import Coordinates
import numpy as np
import pandas as pd
import FastKnn
import logging
from collections import defaultdict

import PreReqs
from PreReqs import WikiBrainNumbering
from sklearn.cluster import KMeans
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from AugmentMatrix import AugmentLabel

global clusterCenters


class RegionCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class MakeSampleRegions(MTimeMixin, luigi.Task):
    '''
    Run KMeans to cluster article points into specific continents.
    Seed is set at 42 to make sure that when run against labeling
    algorithm clusters numbers consistently refer to the same entity
    '''

    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                       "clusters_with_id"))

    def requires(self):
        config = MapConfig.get()
        return (
            RegionCode(),
            AugmentLabel(),
            # FIXME: Circular dependency
            # Coordinates.CreateSampleCoordinates(),
            PreReqs.SampleCreator(config.get("GeneratedFiles",
                                             "vecs_with_labels")),
            PreReqs.EnsureDirectoriesExist(),
        )

    def run(self):
        config = MapConfig.get()
        featureDict = Utils.read_vectors(config.getSample("GeneratedFiles", "vecs_with_labels"))
        vectors = np.array([list(i) for i in featureDict['vector']])

        # labels = list(KMeans((config.getint("PreprocessingConstants",
        #                                     "num_clusters")),
        #                      random_state=42).fit(vectors).labels_)
        kMeans = KMeans((config.getint("PreprocessingConstants",
                                            "num_clusters")),
                             random_state=42).fit(vectors)
        labels = list(kMeans.labels_)

        global clusterCenters  # For unittest
        clusterCenters = kMeans.cluster_centers_

        data = {'index': featureDict.index, 'cluster': labels}
        result = pd.DataFrame(data, columns=['index', 'cluster'])
        result.set_index('index', inplace=True)
        result.sort_index(inplace=True)
        result.to_csv(config.getSample("GeneratedFiles", "clusters_with_id"), sep='\t', index_label='index',
                      columns=['cluster'])

def test_MakeSampleRegions_task():
    config = MapConfig.initTest()
    # Create a unit test config object
    testSampleRegion = MakeSampleRegions()
    testSampleRegion.run()
    assert testSampleRegion is not None

    clusters = pd.read_table(config.getSample("GeneratedFiles", "clusters_with_id"), index_col= 'index')

    # All points in a cluster are closer to its centroid than to other centroids
    global clusterCenters
    vecs = Utils.read_vectors(config.getSample("GeneratedFiles", "vecs_with_labels"))
    clusters.index = clusters.index.astype(str)
    for i, (index, row) in enumerate(vecs.iterrows()):
        centroid = clusterCenters[clusters.loc[index]['cluster']]  # Centroid of cluster this vector is in
        centroidDist = np.sum((centroid - row['vector']) * (centroid - row['vector']))
        for center in clusterCenters:
            centerdDist = np.sum((center - row['vector']) * (center - row['vector']))
            assert centerdDist >= centroidDist

    # Neighbors of a point should also be in the same cluster
    vecs = Utils.read_vectors(config.get("GeneratedFiles", "vecs_with_labels"))
    vecsdf = pd.read_table(config.get("GeneratedFiles", "vecs_with_labels"), skiprows=1,
                           skip_blank_lines=True,
                           header=None, index_col=0)  # Vectors are merged in one column
    features = pd.merge(vecs, clusters, how='inner', left_index=True, right_index=True)
    stat = []
    for i, (index, row) in enumerate(features.iterrows()):
        dist = vecsdf - row['vector']
        vectorDist = dist * dist
        vectorDist['distance'] = vectorDist.sum(axis=1)
        vectorDist.sort_values('distance', inplace=True)
        vectorDist.index = vectorDist.index.astype(str)
        top10Vec = vectorDist.index[:10]  # 10 nearest neighbors of this point
        clusterOfNeighbor = clusters.loc[top10Vec]['cluster']  # List of clusters that neighbors belong to
        cluster = clusters.loc[index]['cluster']  # Cluster this point belongs to
        preserved = clusterOfNeighbor[clusterOfNeighbor == cluster].count()
        stat.append(preserved)
    assert np.mean(stat) >= 4

class CreateSampleRegionIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        config = MapConfig.get()
        super(CreateSampleRegionIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.getSample("GeneratedFiles", "vecs_with_labels")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        config = MapConfig.get()
        return WikiBrainNumbering(), PreReqs.SampleCreator(config.get("GeneratedFiles", "vecs_with_labels"))

    def output(self):
        return TimestampedLocalTarget(self.knn.pathAnnoy), TimestampedLocalTarget(self.knn.pathIds)

    def run(self):
        self.knn.rebuild()


class MakeRegions(MTimeMixin, luigi.Task):
    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles",
                                                 "clusters_with_id"))

    def requires(self):
        config = MapConfig.get()
        if config.sampleBorders():
            return (
                MakeSampleRegions(),
                WikiBrainNumbering(),
                PreReqs.EnsureDirectoriesExist(),
                CreateSampleRegionIndex(),
                AugmentLabel(),
            )
        else:
            return (
                WikiBrainNumbering(),
                PreReqs.EnsureDirectoriesExist(),
                AugmentLabel(),
            )

    def run(self):
        config = MapConfig.get()

        vecs = Utils.read_vectors(config.get("GeneratedFiles", "vecs_with_labels"))

        if config.sampleBorders():
            logger = logging.getLogger('workload')
            sampleRegions = pd.read_table(config.getSample("GeneratedFiles", "clusters_with_id"), index_col='index')
            sampleRegions.index = sampleRegions.index.astype(str)
            knn = FastKnn.FastKnn(config.getSample("GeneratedFiles", "vecs_with_labels"))
            assert (knn.exists())
            knn.read()
            ids = []
            clusters = []
            for i, (id, row) in enumerate(vecs.iterrows()):
                if i % 10000 == 0:
                    logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
                if id in sampleRegions.index:
                    cluster = sampleRegions.loc[id]['cluster']
                else:
                    sums = defaultdict(float)
                    if len(row['vector']) == 0: continue
                    hood = knn.neighbors(row['vector'], 5)
                    if not hood: continue
                    for (id2, score) in hood:
                        c = sampleRegions.loc[id2]['cluster']
                        if c is not None and score > 0:
                            sums[c] += score
                    if not sums: continue
                    cluster = max(sums, key=sums.get)
                ids.append(id)
                clusters.append(cluster)
        else:
            ids = list(k for k in vecs.index if len(vecs.loc[k]['vector']) > 0)
            vectors = np.array([list(i) for i in vecs['vector']])
            clusters = list(KMeans((config.getint("PreprocessingConstants",
                                                  "num_clusters")),
                                   random_state=42).fit(vectors).labels_)

        data = {'index': ids, 'cluster': clusters}
        result = pd.DataFrame(data, columns=['index', 'cluster'])
        result.set_index('index', inplace=True)
        result.sort_index(inplace=True)
        result.to_csv(config.get("GeneratedFiles", "clusters_with_id"), sep='\t', index_label='index',
                      columns=['cluster'])

def test_MakeRegions_task():
    # sample_size in config == 50
    config = MapConfig.initTest()
    knn = FastKnn.FastKnn(config.getSample("GeneratedFiles", "vecs_with_labels"))
    knn.rebuild()

    # First get regions for samples to get centroids
    testSampleRegion = MakeSampleRegions()
    testSampleRegion.run()

    # Then run on everything
    testRegion = MakeRegions()
    testRegion.run()

    assert testRegion is not None

    clusters = pd.read_table(config.get("GeneratedFiles", "clusters_with_id"), index_col= 'index')

    global clusterCenters
    # All points in a cluster are closer to its centroid than to other centroids
    vecs = Utils.read_vectors(config.get("GeneratedFiles", "vecs_with_labels"))
    clusters.index = clusters.index.astype(str)
    count = 0
    for i, (index, row) in enumerate(vecs.iterrows()):
        if index in clusters.index:
            centroid = clusterCenters[clusters.loc[index]['cluster']]  # Centroid of cluster this vector is in
            centroidDist = np.sum((centroid - row['vector']) * (centroid - row['vector']))
            for center in clusterCenters:
                centerdDist = np.sum((center - row['vector']) * (center - row['vector']))
                if centerdDist >= centroidDist:
                    count += 1

    # Neighbors of a point should also be in the same cluster
    vecs = Utils.read_vectors(config.get("GeneratedFiles", "vecs_with_labels"))
    vecsdf = pd.read_table(config.get("GeneratedFiles", "vecs_with_labels"), skiprows=1,
                           skip_blank_lines=True,
                           header=None, index_col=0)  # Vectors are merged in one column
    features = pd.merge(vecs, clusters, how='inner', left_index=True, right_index=True)
    stat = []
    for i, (index, row) in enumerate(features.iterrows()):
        dist = vecsdf - row['vector']
        vectorDist = dist * dist
        vectorDist['distance'] = vectorDist.sum(axis=1)
        vectorDist.sort_values('distance', inplace=True)
        vectorDist.index = vectorDist.index.astype(str)
        top10Vec = vectorDist.index[:10]  # 10 nearest neighbors of this point
        clusterOfNeighbor = clusters.loc[top10Vec]['cluster']  # List of clusters that neighbors belong to
        cluster = clusters.loc[index]['cluster']  # Cluster this point belongs to
        preserved = clusterOfNeighbor[clusterOfNeighbor == cluster].count()
        stat.append(preserved)
    assert np.mean(stat) >= 5


