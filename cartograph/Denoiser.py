from pygsp import graphs, filters
import numpy as np


class Denoiser:

    def __init__(self, x, y, clusters, waterLevel):
        self.waterLevel = waterLevel
        self.x, self.y, self.clusters = self._add_water(x, y, clusters)
        self.num_clusters = len(set(self.clusters))

    def _make_filter(self, tau=10):
        graph = graphs.NNGraph(zip(self.x, self.y), k=self.num_clusters)
        graph.estimate_lmax()
        # higher tau, spikier signal, less points
        fn = filters.Heat(graph, tau=tau)
        return fn

    def _filter_in(self):
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
        signal = self._filter_in()
        max_idx_arr = np.argmax(signal, axis=0)
        keep = []
        for i in range(len(self.x)):
            if max_idx_arr[i] == self.clusters[i]:
                keep.append(True)
            else:
                keep.append(False)
        return keep, list(self.x), list(self.y), list(self.clusters)
