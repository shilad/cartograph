import luigi
import Config
import Utils
import Coordinates
import numpy as np
import FastKnn
import logging
from collections import defaultdict

import cartograph.PreReqs
from PreReqs import WikiBrainNumbering
from sklearn.cluster import KMeans
from LuigiUtils import MTimeMixin, TimestampedLocalTarget


class RegionCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(__file__))

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
            cartograph.PreReqs.SampleCreator(config.get("ExternalFiles",
                                                 "vecs_with_id")),
            cartograph.EnsureDirectoriesExist(),
        )

    def run(self):
        config = Config.get()
        featureDict = Utils.read_features(config.getSample("ExternalFiles",
                                                           "vecs_with_id"))
        keys = list(k for k in featureDict.keys() if len(featureDict[k]['vector']) > 0)
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        labels = list(KMeans((config.getint("PreprocessingConstants",
                                            "num_clusters")),
                             random_state=42).fit(vectors).labels_)

        Utils.write_tsv(config.getSample("GeneratedFiles", "clusters_with_id"),
                        ("index", "cluster"), keys, labels)


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
                cartograph.EnsureDirectoriesExist(),
                Coordinates.CreateSampleAnnoyIndex()
            )
        else:
            return (
                WikiBrainNumbering(),
                cartograph.EnsureDirectoriesExist(),
            )

    def run(self):
        config = Config.get()
        if config.sampleBorders():
            logger = logging.getLogger('workload')
            sampleRegions = Utils.read_features(config.getSample("GeneratedFiles", "clusters_with_id"))
            vecs = Utils.read_features(config.get("ExternalFiles", "vecs_with_id"))
            knn = FastKnn.FastKnn(config.getSample("ExternalFiles",
                                                   "vecs_with_id"))
            assert(knn.exists())
            knn.read()
            ids = []
            clusters = []
            for i, (id, row) in enumerate(vecs.items()):
                if i % 10000 == 0:
                    logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
                if id in sampleRegions:
                    cluster = sampleRegions[id]['cluster']
                else:
                    sums = defaultdict(float)
                    if len(row['vector']) == 0: continue
                    hood = knn.neighbors(row['vector'], 5)
                    if not hood: continue
                    for (id2, score) in hood:
                        c = sampleRegions[id2].get('cluster')
                        if c is not None and score > 0:
                            sums[c] += score
                    if not sums: continue
                    cluster = max(sums, key=sums.get)
                ids.append(id)
                clusters.append(cluster)
        else:
            featureDict = Utils.read_features(config.get("ExternalFiles",
                                                         "vecs_with_id"))
            ids = list(k for k in featureDict.keys() if len(featureDict[k]['vector']) > 0)
            vectors = np.array([featureDict[vID]["vector"] for vID in ids])
            clusters = list(KMeans((config.getint("PreprocessingConstants",
                                                "num_clusters")),
                                 random_state=42).fit(vectors).labels_)

        Utils.write_tsv(config.get("GeneratedFiles", "clusters_with_id"),
                        ("index", "cluster"), ids, clusters)
