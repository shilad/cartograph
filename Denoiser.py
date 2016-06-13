from pygsp import graphs, filters
import numpy as np


class Denoiser:
    def __init__(self, x, y, clusters):
        self.x = x
        self.y = y
        self.clusters = clusters

    def _make_filter(self):
        graph = graphs.NNGraph([self.x, self.y])
        graph.estimate_lmax()  # k = 10
        fn = filters.Heat(graph)  # tau = 10, higher tau, spikier signal, less points
        return fn

    def _filter_in(self):
        n = len(self.x)
        num_clusters = len(self.clusters)
        filter_ = self._make_filter()
        signal = np.empty(n * num_clusters).reshape(num_clusters, n)

