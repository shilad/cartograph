import luigi
import os
import time
from src import Constants, Util, Denoiser
from tsne import bh_sne
import numpy as np
from sklearn.cluster import KMeans


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


class LabelNames(luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(Constants.FILE_NAME_REGION_NAMES))


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
            lines = nameFile.readlines()[1:]
            Util.write_tsv(Constants.FILE_NAME_NUMBERED_NAMES,
                           ("index", "name"), range(1, len(lines) + 1), lines)

        with open(Constants.FILE_NAME_WIKIBRAIN_VECS) as nameFile:
            lines = nameFile.readlines()[1:]
            Util.write_tsv(Constants.FILE_NAME_NUMBERED_VECS,
                           ("index", "vector"),
                           range(1, len(lines) + 1), lines)


class RegionClustering(MTimeMixin, luigi.Task):
    def output(self):
        return luigi.LocalTarget(Constants.FILE_NAME_NUMBERED_CLUSTERS)

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        featureDict = Util.read_features(Constants.FILE_NAME_NUMBERED_VECS)
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vectorID]["vector"] for vectorID in keys])
        labels = list(KMeans(Constants.NUM_CLUSTERS,
                             random_state=42).fit(vectors).labels_)
        print len(labels)
        Util.write_tsv(Constants.FILE_NAME_NUMBERED_CLUSTERS,
                       ("index", "cluster"), keys, labels)


class Embedding(MTimeMixin, luigi.Task):
    def output(self):
        return luigi.LocalTarget(Constants.FILE_NAME_ARTICLE_COORDINATES)

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        featureDict = Util.read_features(Constants.FILE_NAME_NUMBERED_VECS)
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vectorID]["vector"] for vectorID in keys])
        out = bh_sne(vectors,
                     pca_d=Constants.TSNE_PCA_DIMENSIONS,
                     theta=Constants.TSNE_THETA)
        x, y = list(out[:, 0]), list(out[:, 1])
        Util.write_tsv(Constants.FILE_NAME_TSNE_CACHE,
                       ("index", "x", "y"), keys, x, y)


class Denoise(MTimeMixin, luigi.Task):
    def output(self):
        return (
            luigi.LocalTarget(Constants.FILE_NAME_KEEP)
        )

    def requires(self):
        return RegionClustering(), Embedding()

    def run(self):
        featureDict = Util.read_features(Constants.FILE_NAME_ARTICLE_COORDINATES,
                                         Constants.FILE_NAME_NUMBERED_CLUSTERS)
        featureIDs = list(featureDict.keys())
        x = [float(featureDict[featureID]["x"]) for featureID in featureIDs]
        y = [float(featureDict[featureID]["y"]) for featureID in featureIDs]
        c = [int(featureDict[featureID]["cluster"]) for featureID in featureIDs]

        denoiser = Denoiser.Denoiser(x, y, c)
        keepBooleans = denoiser.denoise()

        Util.write_tsv(Constants.FILE_NAME_KEEP, ("index", "keep"),
                       featureIDs, keepBooleans)
