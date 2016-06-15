import numpy as np
from tsne import bh_sne
from sklearn.cluster import KMeans
from Denoiser import Denoiser
import Constants
import Util


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
        Util.write_tsv(Constants.FILE_NAME_COORDS_AND_CLUSTERS, ["x", "y", "clusters"], [self.x, self.y, self.clusters])
        Util.write_tsv(Constants.FILE_NAME_NAMES_AND_CLUSTERS, ["names", "clusters"], [self.names, self.clusters])

    @staticmethod
    def _read_wikibrain_out():
        matrix = Util.read_wikibrain_vecs()
        names = Util.read_tsv(Constants.FILE_NAME_WIKIBRAIN_NAMES)
        return np.array(matrix), names[0]

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
    analyzer.save_to_files()