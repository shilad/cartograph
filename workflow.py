import luigi
import os
import time
import Constants
import Util
from tsne import bh_sne
import numpy as np


class MTimeMixin:
    """
        Mixin that flags a task as incomplete if any requirement
        is incomplete or has been updated more recently than this task
        This is based on http://stackoverflow.com/a/29304506, but extends
        it to support multiple input / output dependencies.
    """

    def complete(self):
        def to_list(obj):
            if type(obj) in (type(()), type([])):
                return obj
            else:
                return [obj]

        def mtime(path):
            return time.ctime(os.path.getmtime(path))

        if not all(os.path.exists(out.path) for out in to_list(self.output())):
            return False

        self_mtime = min(mtime(out.path) for out in to_list(self.output()))

        # the below assumes a list of requirements,
        # each with a list of outputs. YMMV
        for el in to_list(self.requires()):
            if not el.complete():
                return False
            for output in to_list(el.output()):
                if mtime(output.path) > self_mtime:
                    return False

        return True


class WikiBrainData(luigi.ExternalTask):
    def output(self):
        return (
            luigi.LocalTarget(Constants.FILE_NAME_WIKIBRAIN_NAMES),
            luigi.LocalTarget(Constants.FILE_NAME_WIKIBRAIN_VECS),
        )


class WikiBrainNumbering(MTimeMixin, luigi.Task):
    def output(self):
        return (
            luigi.LocalTarget(Constants.FILE_NAME_NUMBERED_VECS),
            luigi.LocalTarget(Constants.FILE_NAME_NUMBERED_NAMES),
        )

    def requires(self):
        return WikiBrainData()

    def run(self):
        with open(Constants.FILE_NAME_WIKIBRAIN_NAMES) as nameFile:
            lines = nameFile.readlines()
            with open(Constants.FILE_NAME_NUMBERED_NAMES, "w") as numberNames:
                for i, line in enumerate(lines):
                    numberNames.write('%d\t%s' % (i + 1, line))

        with open(Constants.FILE_NAME_WIKIBRAIN_VECS) as nameFile:
            lines = nameFile.readlines()
            with open(Constants.FILE_NAME_NUMBERED_VECS, "w") as numberNames:
                for i, line in enumerate(nameFile.readlines()):
                    numberNames.write('%d\t%s' % (i + 1, line))


class RegionClustering(MTimeMixin, luigi.Task):
    def output(self):
        return luigi.LocalTarget("data/cluster_labels.tsv")

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        f = open('data/cluster_labels.tsv', 'w')
        f.write('writing DATA\n')
        f.close()


class Embedding(MTimeMixin, luigi.Task):
    def output(self):
        return luigi.LocalTarget(Constants.FILE_NAME_TSNE_CACHE)

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        featureDict = Util.read_features(Constants.FILE_NAME_NUMBERED_VECS)
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vectorID]["vector"] for vectorID in keys])
        out = bh_sne(vectors,
                     pca_d=Constants.TSNE_PCA_DIMENSIONS,
                     theta=Constants.TSNE_THETA)
        x, y = out[:, 0], out[:, 1]
        Util.write_tsv(Constants.FILE_NAME_TSNE_CACHE, ("x", "y"), (x, y))


class DenoiseAndAddWater(MTimeMixin, luigi.Task):
    def output(self):
        return (
            luigi.LocalTarget("data/coords_and_clusters.tsv"),
            luigi.LocalTarget("data/names_and_clusters.tsv")
        )

    def requires(self):
        return RegionClustering(), Embedding()

    def run(self):
        for fn in ("data/coords_and_clusters.tsv",
                   "data/names_and_clusters.tsv"):
            f = open(fn, 'w')
            f.write('writing DATA\n')
            f.close()

