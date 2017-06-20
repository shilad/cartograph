import luigi
import Config
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
        config = Config.get()
        return TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                       "clusters_with_id"))

    def requires(self):
        config = Config.get()
        return (
            RegionCode(),
            Coordinates.CreateSampleCoordinates(),
            PreReqs.SampleCreator(config.get("ExternalFiles",
                                             "best_vecs_with_id")),
            PreReqs.EnsureDirectoriesExist(),
        )

    def run(self):
        config = Config.get()
        # featureDict = Utils.read_features(config.getSample("ExternalFiles",
        #                                                    "best_vecs_with_id"))
        # keys = list(k for k in featureDict.keys() if len(featureDict[k]['vector']) > 0)
        # results = list(map(int, keys))
        # results.sort()
        # keys = list(map(str, results))
        #
        # print keys
        #
        # vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        # print vectors
        # labels = list(KMeans((config.getint("PreprocessingConstants",
        #                                     "num_clusters")),
        #                      random_state=42).fit(vectors).labels_)
        #
        # Utils.write_tsv(config.getSample("GeneratedFiles", "clusters_with_id"),
        #                 ("index", "cluster"), keys, labels)
        #
        featureDict = pd.read_table(config.getSample("ExternalFiles",
                                                     "best_vecs_with_id"), skiprows=1, skip_blank_lines=True,
                                    header=None)
        featureDict['vectorTemp'] = featureDict.iloc[:, 1:].apply(lambda x: tuple(x),
                                                                  axis=1)  # join all vector columns into same column
        featureDict.drop(featureDict.columns[1:-1], axis=1,
                         inplace=True)  # drop all columns but the index and the vectorTemp column
        featureDict.columns = ['index', 'vector']
        featureDict = featureDict.set_index('index')

        vectors = [list(i) for i in featureDict['vector']]
        vectors = np.array(vectors)

        labels = list(KMeans((config.getint("PreprocessingConstants",
                                            "num_clusters")),
                             random_state=42).fit(vectors).labels_)

        data = {'index': featureDict.index, 'cluster': labels}
        result = pd.DataFrame(data, columns=['index', 'cluster'])
        result.set_index('index', inplace=True)
        result.sort_index(inplace=True)
        result.to_csv(config.getSample("GeneratedFiles", "clusters_with_id"), sep='\t', index_label='index',
                      columns=['cluster'])


def test_MakeSampleRegions_task():
    # sample_size in config == 50
    Config.initTest()
    # Create a unit test config object
    testSampleRegion = MakeSampleRegions()
    testSampleRegion.run()
    assert testSampleRegion is not None
    correct = pd.read_table('./data/test/tsv/numberedClusters.sample_50_correct.tsv', index_col='index')
    result = pd.read_table('./data/test/tsv/numberedClusters.sample_50.tsv', index_col='index')
    for (id1, row1), (id2, row2) in zip(correct.iterrows(), result.iterrows()):
        assert id1 == id2
        assert row1['cluster'] == row2['cluster']


class MakeRegions(MTimeMixin, luigi.Task):
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles",
                                                 "clusters_with_id"))

    def requires(self):
        config = Config.get()
        if config.sampleBorders():
            return (
                MakeSampleRegions(),
                WikiBrainNumbering(),
                PreReqs.EnsureDirectoriesExist(),
                Coordinates.CreateSampleAnnoyIndex()
            )
        else:
            return (
                WikiBrainNumbering(),
                PreReqs.EnsureDirectoriesExist(),
            )

    def run(self):
        config = Config.get()

        vecs = pd.read_table(config.get("ExternalFiles", "vecs_with_id"), skip_blank_lines=True, skiprows=1,
                             header=None)
        vecs['vectorTemp'] = vecs.iloc[:, 1:].apply(lambda x: tuple(x),
                                                    axis=1)  # join all vector columns into same column
        vecs.drop(vecs.columns[1:-1], axis=1,
                  inplace=True)  # drop all columns but the index and the vectorTemp column
        vecs.columns = ['index', 'vector']
        vecs = vecs.set_index('index')

        if config.sampleBorders():
            logger = logging.getLogger('workload')
            sampleRegions = pd.read_table(config.getSample("GeneratedFiles", "clusters_with_id"), index_col='index')
            knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
            assert (knn.exists())
            knn.read()
            ids = []
            clusters = []
            for i, (id, row) in enumerate(vecs.iterrows()):
                if i % 10000 == 0:
                    logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
                if id in sampleRegions.index and sampleRegions.loc[id]['cluster']:
                    cluster = sampleRegions.loc[id]['cluster']
                else:
                    sums = defaultdict(float)
                    if len(row['vector']) == 0: continue
                    hood = knn.neighbors(row['vector'], 5)
                    if not hood: continue
                    for (id2, score) in hood:
                        if id2.isdigit():
                            c = sampleRegions.loc[int(id2)]['cluster']
                        if c is not None and score > 0:
                            sums[c] += score
                    if not sums: continue
                    cluster = max(sums, key=sums.get)
                ids.append(id)
                clusters.append(cluster)

        else:
            ids = list(k for k in vecs.index if len(vecs.loc[k]['vector']) > 0)
            vectors = [list(i) for i in vecs['vector']]
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
    config = Config.initTest()
    knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
    knn.rebuild()

    testRegion = MakeRegions()
    testRegion.run()
    assert testRegion is not None

    correct = pd.read_table('./data/test/tsv/numberedClusters_correct.tsv', index_col='index')
    correct.sort_index(inplace=True)
    correct.to_csv('./data/test/tsv/numberedClusters_correct.tsv', sep='\t', index_label='index',
                  columns=['cluster'])
    result = pd.read_table('./data/test/tsv/numberedClusters.tsv', index_col='index')
    for (id1, row1), (id2, row2) in zip(correct.iterrows(), result.iterrows()):
        assert id1 == id2
        assert row1['cluster'] == row2['cluster']
