from __future__ import  print_function
import os
import numpy as np
from tsne import bh_sne
from sklearn.cluster import KMeans
from Denoiser import Denoiser
import Constants
import Util


class Analyzer:

    def __init__(self, subset=0, save_output=True, use_cache=True):
        self.vecs, self.names = self._read_wikibrain_out()
        if subset:
            self.vecs = self.vecs[:subset]
            self.names = self.names[:subset]
        self.x = []
        self.y = []
        self.clusters = []
        self.save_output = save_output
        self.use_cache = use_cache

    def save_to_files(self, filename1, filename2):
        Util.write_tsv(filename1, ["x", "y", "clusters"], [self.x, self.y, self.clusters])
        Util.write_tsv(filename2, ["names", "clusters"], [self.names, self.clusters])

    @staticmethod
    def _read_wikibrain_out():
        matrix = Util.read_wikibrain_vecs()
        names = Util.read_tsv(Constants.FILE_NAME_WIKIBRAIN_NAMES)
        return np.array(matrix), names["names"]

    @staticmethod
    def _do_tSNE(vecs):
        out = bh_sne(vecs, pca_d=Constants.TSNE_PCA_DIMENSIONS, theta=Constants.TSNE_THETA)
        return out[:, 0], out[:, 1]

    @staticmethod
    def _add_water(x, y, clusters, names):
        length = len(x)
        water_x = np.random.uniform(np.min(x)-3, np.max(x)+3, int(length*Constants.PERCENTAGE_WATER))
        water_y = np.random.uniform(np.min(y)-3, np.max(y)+3, int(length*Constants.PERCENTAGE_WATER))
        x = np.append(x, water_x)
        y = np.append(y, water_y)
        clusters = np.append(clusters, np.full(int(length*Constants.PERCENTAGE_WATER), max(clusters)+1, dtype=np.int))
        names = np.append(names, np.full(int(length*Constants.PERCENTAGE_WATER), max(clusters)+1, dtype = np.int))
        return x, y, clusters, names

    @staticmethod
    def _do_k_means(vecs):
        return KMeans(Constants.NUM_CLUSTERS, random_state=42).fit(vecs).labels_

    @staticmethod
    def _denoise(x, y, clusters, names):
        return Denoiser(x, y, clusters, names).denoise()

    def analyze(self):
        print("Analyzing")
        if self.use_cache and os.path.exists(Constants.FILE_NAME_TSNE_CACHE):
            print("Using cache for t-SNE")
            file_out = Util.read_tsv(Constants.FILE_NAME_TSNE_CACHE)
            self.x = map(float, file_out["x"])
            self.y = map(float, file_out["y"])
        else:
            print("Doing t-SNE...")
            self.x, self.y = self._do_tSNE(self.vecs)
            Util.write_tsv(Constants.FILE_NAME_TSNE_CACHE, ("x", "y"), (self.x, self.y))
        print("t-SNE done")

        print("Doing k-means...")
        self.clusters = self._do_k_means(self.vecs)
        print("k-means done")

        print("Adding water...")
        self.x, self.y, self.clusters, self.names = self._add_water(self.x, self.y, self.clusters, self.names)
        print("Adding water done")

        print("Denoising...")
        self.x, self.y, self.clusters, self.names = self._denoise(self.x, self.y, self.clusters, self.names)
        print("Denoising done")

        if self.save_output:
            self.save_to_files(Constants.FILE_NAME_COORDS_AND_CLUSTERS, Constants.FILE_NAME_NAMES_AND_CLUSTERS)
            print("Output saved to", Constants.FILE_NAME_COORDS_AND_CLUSTERS, "and", Constants.FILE_NAME_NAMES_AND_CLUSTERS)
        return self.x, self.y, self.clusters, self.names


if __name__ == '__main__':
    Analyzer(save_output=True, use_cache=True).analyze()