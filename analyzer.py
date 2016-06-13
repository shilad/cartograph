import numpy as np
from tsne import bh_sne
from sklearn.cluster import KMeans
import codecs
from Denoiser import Denoiser


class Analyzer:

    def __init__(self, vec_filename, names_filename, subset=0):
        self.vecs, self.names = self._read_wikibrain_out(vec_filename, names_filename)
        if subset:
            self.vecs = self.vecs[:subset]
            self.names = self.names[:subset]
        self.x = []
        self.y = []
        self.clusters = []

    def __str__(self):
        s = ",".join(("x", "y", "clusters", "names")) + "\n"
        for i in range(len(self.x)):
            s += ",".join((str(self.x[i]), str(self.y[i]), str(self.clusters[i]), self.names[i])) + "\n"
        return s.encode("utf-8")

    def to_file(self, filename="./data/data.csv"):
        with open(filename, mode="w") as f:
            f.write(str(self))

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
        self.x, self.y, self.clusters = Denoiser(self.x, self.y, self.clusters).denoise()

    def analyze(self):
        print "Analyzing"
        self._do_tSNE()
        print "t-SNE done"
        # self._do_k_means()
        # print "k-means done"
        self._denoise()
        return self.x, self.y, self.clusters, self.names


analyzer = Analyzer("./data/vecs.csv", "./data/names.csv", subset=1000)
x, y, clusters, names = analyzer.analyze()
analyzer.to_file("./data/testing.csv")