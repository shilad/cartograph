from pygsp import graphs, filters
import numpy as np
import Config
import Utils
import luigi
import Coordinates
from Regions import MakeRegions
from LuigiUtils import MTimeMixin, TimestampedLocalTarget


class DenoiserCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class Denoise(MTimeMixin, luigi.Task):
    '''
    Remove outlier points and set water level for legibility in reading
    and more coherent contintent boundary lines
    '''
    def output(self):
        config = Config.get()
        return (
            TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                    "denoised_with_id")),
            TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                    "clusters_with_water")),
            TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                    "coordinates_with_water"))
        )

    def requires(self):
        return (MakeRegions(),
                Coordinates.CreateSampleCoordinates(),
                DenoiserCode())

    def run(self):
        config = Config.get()
        featureDict = Utils.read_features(config.getSample("GeneratedFiles", "article_coordinates"),
                                          config.getSample("GeneratedFiles",
                                                           "clusters_with_id"))
        featureIDs = list(featureDict.keys())
        x = [float(featureDict[fID]["x"]) for fID in featureIDs]
        y = [float(featureDict[fID]["y"]) for fID in featureIDs]
        c = [int(featureDict[fID]["cluster"]) for fID in featureIDs]

        denoiser = Denoiser(x, y, c,
                                     config.getfloat("PreprocessingConstants",
                                                     "water_level"))
        keepBooleans, waterX, waterY, waterCluster = denoiser.denoise()

        for x in range(len(waterX) - len(featureIDs)):
            featureIDs.append("w" + str(x))

        Utils.write_tsv(config.getSample("GeneratedFiles",
                                         "denoised_with_id"),
                        ("index", "keep"),
                        featureIDs, keepBooleans)

        Utils.write_tsv(config.getSample("GeneratedFiles",
                                         "coordinates_with_water"),
                        ("index", "x", "y"), featureIDs, waterX, waterY)
        Utils.write_tsv(config.getSample("GeneratedFiles", "clusters_with_water"),
                        ("index", "cluster"), featureIDs, waterCluster)


class Denoiser:

    def __init__(self, x, y, clusters, waterLevel):
        self.waterLevel = waterLevel
        self.x, self.y, self.clusters = self._add_water(x, y, clusters)
        self.num_clusters = len(set(self.clusters))

    def _make_filter(self, tau=10):
        '''
        Build graph and heatmap for denoising.
        '''
        graph = graphs.NNGraph(zip(self.x, self.y), k=self.num_clusters)
        graph.estimate_lmax()
        # higher tau, spikier signal, less points
        fn = filters.Heat(graph, tau=tau)
        return fn

    def _filter_in(self):
        '''
        Build matrix and do the filtering
        '''
        n = len(self.x)
        filter_ = self._make_filter()
        signal = np.empty(self.num_clusters * n).reshape(self.num_clusters, n)
        vectors = np.zeros(n * self.num_clusters).reshape(n, self.num_clusters)
        for i, vec in enumerate(vectors):
            vec[self.clusters[i]] = 1
        vectors = vectors.T
        for cluster_num, vec in enumerate(vectors):
            signal[cluster_num] = filter_.analysis(vec)
        return signal

    def _add_water(self, x, y, clusters):
        length = len(x)
        water_x = np.random.uniform(np.min(x) - 3,
                                    np.max(x) + 3,
                                    int(length * self.waterLevel))
        water_y = np.random.uniform(np.min(x) - 3,
                                    np.max(x) + 3,
                                    int(length * self.waterLevel))
        x = np.append(x, water_x)
        y = np.append(y, water_y)
        clusters = np.append(clusters,
                             np.full(int(length * self.waterLevel),
                                     max(clusters) + 1, dtype=np.int))
        return x, y, clusters

    def denoise(self):
        '''
        Return the denoised data
        '''
        signal = self._filter_in()
        max_idx_arr = np.argmax(signal, axis=0)
        keep = []
        for i in range(len(self.x)):
            if max_idx_arr[i] == self.clusters[i]:
                keep.append(True)
            else:
                keep.append(False)
        return keep, list(self.x), list(self.y), list(self.clusters)
