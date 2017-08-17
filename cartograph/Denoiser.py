from pygsp import graphs, filters
import numpy as np
import MapConfig
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
        config = MapConfig.get()
        if config.sampleBorders():
            return (
                TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                        "denoised_with_id")),
                TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                        "clusters_with_water")),
                TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                        "coordinates_with_water"))
            )
        else:
            return (
                TimestampedLocalTarget(config.get("GeneratedFiles",
                                                  "denoised_with_id")),
                TimestampedLocalTarget(config.get("GeneratedFiles",
                                                  "clusters_with_water")),
                TimestampedLocalTarget(config.get("GeneratedFiles",
                                                  "coordinates_with_water"))
            )

    def requires(self):
        if MapConfig.get().sampleBorders():
            return (MakeRegions(),
                    Coordinates.CreateSampleCoordinates(),
                    DenoiserCode())
        else:
            return (MakeRegions(),
                    Coordinates.CreateFullCoordinates(),
                    DenoiserCode())

    def run(self):
        config = MapConfig.get()
        if config.sampleBorders():
            featureDict = Utils.read_features(config.getSample("GeneratedFiles", "article_coordinates"),
                                              config.getSample("GeneratedFiles", "clusters_with_id"),
                                              required=("x", "y", "cluster"))
        else:
            featureDict = Utils.read_features(config.get("GeneratedFiles", "article_coordinates"),
                                              config.get("GeneratedFiles", "clusters_with_id"),
                                              required=("x", "y", "cluster"))
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

        if config.sampleBorders():
            Utils.write_tsv(config.getSample("GeneratedFiles",
                                             "denoised_with_id"),
                            ("index", "keep"),
                            featureIDs, keepBooleans)

            Utils.write_tsv(config.getSample("GeneratedFiles",
                                             "coordinates_with_water"),
                            ("index", "x", "y"), featureIDs, waterX, waterY)
            Utils.write_tsv(config.getSample("GeneratedFiles", "clusters_with_water"),
                            ("index", "cluster"), featureIDs, waterCluster)
        else:
            Utils.write_tsv(config.get("GeneratedFiles", "denoised_with_id"),
                            ("index", "keep"),
                            featureIDs, keepBooleans)

            Utils.write_tsv(config.get("GeneratedFiles", "coordinates_with_water"),
                            ("index", "x", "y"), featureIDs, waterX, waterY)
            Utils.write_tsv(config.get("GeneratedFiles", "clusters_with_water"),
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
        maxV = max(np.max(np.abs(x)), np.max(np.abs(y)))

        def f(n):
            return (np.random.beta(0.8, 0.8, n) - 0.5) * 2 * (maxV + 5)


        length = len(x)
        water_x = f(int(length * self.waterLevel))
        water_y = f(int(length * self.waterLevel))

        # These are heuristics
        num_squares = 5
        square_dot_sep = 2.0 * maxV / (length * self.waterLevel)

        # Create nested squares around outside to prevent land masses from touching borders.
        for i in range(num_squares):
            sz = maxV + 1.0 * i / num_squares
            n = np.arange(-maxV, maxV, square_dot_sep).shape[0]
            # coordinates for points on top, right, bottom, left of square
            square_x = np.concatenate([
                np.arange(-maxV, maxV, square_dot_sep),
                np.repeat(maxV, n),
                np.arange(-maxV, maxV, square_dot_sep),
                np.repeat(-maxV, n)])
            square_y = np.concatenate([
                np.repeat(maxV, n),
                np.arange(-maxV, maxV, square_dot_sep),
                np.repeat(maxV, n),
                np.arange(-maxV, maxV, square_dot_sep)])
            water_x = np.concatenate([water_x, square_x])
            water_y = np.concatenate([water_y, square_y])

        water_cluster_ids = np.full(water_x.shape[0], max(clusters) + 1, dtype=np.int)

        x = np.append(x, water_x)
        y = np.append(y, water_y)
        clusters = np.append(clusters, water_cluster_ids)
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
