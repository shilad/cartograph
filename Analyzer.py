import numpy as np
from tsne import bh_sne
from sklearn.cluster import KMeans
import codecs
from Denoiser import Denoiser
import Constants


class Analyzer:

    def __init__(self, subset=0, save_output=True):
        self.vecs, self.names = self._read_wikibrain_out()
        if subset:
            self.vecs = self.vecs[:subset]
            self.names = self.names[:subset]
        self.x = []
        self.y = []
        self.clusters = []
        self.save_output = save_output

    def save_to_files(self):
        s = "\t".join(("x", "y", "clusters")) + "\n"
        for i in range(len(self.x)):
            s += "\t".join((str(self.x[i]), str(self.y[i]), str(self.clusters[i]))) + "\n"
        s = s.encode("utf-8")
        with open(Constants.FILE_NAME_COORDS_AND_CLUSTERS, mode="w") as f:
            f.write(s)

        s = "\t".join(("names", "clusters")) + "\n"
        for i in range(len(self.x)):
            s += "\t".join((self.names[i], str(self.clusters[i]))) + "\n"
        s = s.encode("utf-8")
        with open(Constants.FILE_NAME_NAMES_AND_CLUSTERS, mode="w") as f:
            f.write(s)

    @staticmethod
    def _read_wikibrain_out(header=True):
        matrix = []
        names = []
        with open(Constants.FILE_NAME_WIKIBRAIN_VECS, "r") as vecs:
            if header:
                vecs.readline()
            for line in vecs:
                matrix.append(map(float, line.rstrip("\n").split("\t")))
        with codecs.open(Constants.FILE_NAME_WIKIBRAIN_NAMES, "r", encoding="utf-8") as names_file:
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
        self.clusters = KMeans(num_clusters).fit(self.vecs).labels_

    def _denoise(self):
        self.x, self.y, self.clusters, self.names = Denoiser(self.x, self.y, self.clusters, self.names).denoise()

    def analyze(self):
        print "Analyzing"
        self._do_k_means()
        print "k-means done"
        self._do_tSNE()
        print "t-SNE done"
        self._denoise()
        print "Denoising done"
        if self.save_output:
            self.save_to_files()
        return self.x, self.y, self.clusters, self.names


if __name__ == '__main__':
    analyzer = Analyzer(subset=1000, save_output=True)
    analyzer.analyze()
    # analyzer.save_to_files()