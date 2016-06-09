import numpy as np
from tsne import bh_sne
from sklearn.cluster import KMeans
import codecs


class Analyzer:

    def __init__(self, vec_filename, names_filename, subset=False):
        self.vecs, self.names = self._read_wikibrain_out(vec_filename, names_filename)
        if subset:
            self.vecs = self.vecs[:1000]
            self.names = self.names[:1000]
        self.x = []
        self.y = []
        self.clusters = []

    @staticmethod
    def _read_wikibrain_out(vec_filename, names_filename, header=True):
        matrix = []
        names = []
        with open(vec_filename, "r") as vecs:
            if header:
                vecs.readline()
            for line in vecs:
                matrix.append(map(float, line.split(",")))
        with codecs.open(names_filename, "r", encoding="utf-8") as names_file:
            if header:
                names_file.readline()
            for line in names_file:
                names.append(line.rstrip("\n"))
        return np.array(matrix), names

    def _do_tSNE(self, pca_d=None):
        out = bh_sne(self.vecs, pca_d=pca_d)
        self.x = out[:, 0]
        self.y = out[:, 1]

    def _do_k_means(self, num_clusters=10):
        self.clusters = KMeans(num_clusters, n_jobs=-1).fit(self.vecs).labels_

    def _denoise(self):
        # TODO: get denoiser object and pass in x, y, and clusters
        pass

    def analyze(self):
        self._do_k_means()
        self._do_tSNE()
        self._denoise()
        return self.x, self.y, self.clusters, self.names


x, y, clusters, names = Analyzer("data/vecs.csv", "data/names.csv", subset=True).analyze()




