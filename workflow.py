import luigi
import os
import time
from cartograph import Config
from cartograph import Util
from cartograph import Contours
from cartograph import Denoiser
from cartograph import MapStyler
from cartograph.BorderFactory import BorderFactory
from cartograph.BorderGeoJSONWriter import BorderGeoJSONWriter
from tsne import bh_sne
import numpy as np
from sklearn.cluster import KMeans


config = Config.BAD_GET_CONFIG()


class MTimeMixin:
    '''
        Mixin that flags a task as incomplete if any requirement
        is incomplete or has been updated more recently than this task
        This is based on http://stackoverflow.com/a/29304506, but extends
        it to support multiple input / output dependencies.
    '''

    def complete(self):
        def to_list(obj):
            if type(obj) in (type(()), type([])):
                return obj
            else:
                return [obj]

        def mtime(path):
            return os.path.getmtime(path)

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
    '''
    Ensure that all external files produced by WikiBrain exist in
    the correct directory.
    '''

    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_WIKIBRAIN_NAMES),
            luigi.LocalTarget(config.FILE_NAME_WIKIBRAIN_VECS),
        )


class LabelNames(luigi.ExternalTask):
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''

    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_REGION_NAMES))


class WikiBrainNumbering(MTimeMixin, luigi.Task):
    '''
    Number the name and vector output of WikiBrain files so that each
    article has a unique id corrosponding to all of its data for future
    use of any subset of features of interest
    '''

    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_NUMBERED_VECS),
            luigi.LocalTarget(config.FILE_NAME_NUMBERED_NAMES),
        )

    def requires(self):
        return WikiBrainData()

    def run(self):
        with open(config.FILE_NAME_WIKIBRAIN_NAMES) as nameFile:
            lines = nameFile.readlines()[1:]
            Util.write_tsv(config.FILE_NAME_NUMBERED_NAMES,
                           ("index", "name"), range(1, len(lines) + 1), lines)

        with open(config.FILE_NAME_WIKIBRAIN_VECS) as nameFile:
            lines = nameFile.readlines()[1:]
            Util.write_tsv(config.FILE_NAME_NUMBERED_VECS,
                           ("index", "vector"),
                           range(1, len(lines) + 1), lines)


class RegionClustering(MTimeMixin, luigi.Task):
    '''
    Run KMeans to cluster article points into specific continents.
    Seed is set at 42 to make sure that when run against labeling
    algorithm clusters numbers consistantly refer to the same entity
    '''

    def output(self):
        return luigi.LocalTarget(config.FILE_NAME_NUMBERED_CLUSTERS)

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        featureDict = Util.read_features(config.FILE_NAME_NUMBERED_VECS)
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vectorID]["vector"] for vectorID in keys])
        print len(vectors)
        labels = list(KMeans(config.NUM_CLUSTERS,
                             random_state=42).fit(vectors).labels_)
        print len(labels)
        Util.write_tsv(config.FILE_NAME_NUMBERED_CLUSTERS,
                       ("index", "cluster"), keys, labels)


class CreateCoordinates(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes
    '''

    def output(self):
        return luigi.LocalTarget(config.FILE_NAME_ARTICLE_COORDINATES)

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        featureDict = Util.read_features(config.FILE_NAME_NUMBERED_VECS)
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vectorID]["vector"] for vectorID in keys])
        out = bh_sne(vectors,
                     pca_d=config.TSNE_PCA_DIMENSIONS,
                     theta=config.TSNE_THETA)
        x, y = list(out[:, 0]), list(out[:, 1])
        Util.write_tsv(config.FILE_NAME_ARTICLE_COORDINATES,
                       ("index", "x", "y"), keys, x, y)


class Denoise(MTimeMixin, luigi.Task):
    '''
    Remove outlier points and set water level for legibility in reading
    and more coherent contintent boundary lines
    '''

    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_KEEP),
            luigi.LocalTarget(config.FILE_NAME_WATER_CLUSTERS),
            luigi.LocalTarget(config.FILE_NAME_WATER_AND_ARTICLES)
        )

    def requires(self):
        return RegionClustering(), CreateCoordinates()

    def run(self):
        featureDict = Util.read_features(config.FILE_NAME_ARTICLE_COORDINATES,
                                         config.FILE_NAME_NUMBERED_CLUSTERS)
        featureIDs = list(featureDict.keys())
        x = [float(featureDict[featureID]["x"]) for featureID in featureIDs]
        y = [float(featureDict[featureID]["y"]) for featureID in featureIDs]
        c = [int(featureDict[featureID]["cluster"]) for featureID in featureIDs]

        denoiser = Denoiser.Denoiser(x, y, c)
        keepBooleans, waterX, waterY, waterCluster = denoiser.denoise()

        for x in range(len(waterX) - len(featureIDs)):
            featureIDs.append("w" + str(x))
        Util.write_tsv(config.FILE_NAME_KEEP, ("index", "keep"),
                       featureIDs, keepBooleans)
        Util.write_tsv(config.FILE_NAME_WATER_AND_ARTICLES,
                       ("index", "x", "y"), featureIDs, waterX, waterY)
        Util.write_tsv(config.FILE_NAME_WATER_CLUSTERS,
                       ("index", "cluster"), featureIDs, waterCluster)


class CreateContinents(MTimeMixin, luigi.Task):
    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_COUNTRIES),
            luigi.LocalTarget(config.FILE_NAME_REGION_CLUSTERS),
            luigi.LocalTarget(config.FILE_NAME_REGION_BORDERS)
        )

    def requires(self):
        return (Denoise(), LabelNames())

    def decomposeBorders(self, clusterDict):
        regionList = []
        membershipList = []
        for key in clusterDict:
            regions = clusterDict[key]
            for region in regions:
                regionList.append(region)
                membershipList.append(key)
        return regionList, membershipList

    def run(self):
        clusterDict = BorderFactory.from_file().build()
        clusterList = list(clusterDict.values())
        regionList, membershipList = self.decomposeBorders(clusterDict)

        BorderGeoJSONWriter(clusterList).writeToFile(config.FILE_NAME_COUNTRIES)
        Util.write_tsv(config.FILE_NAME_REGION_CLUSTERS,
                       ("region_id", "cluster_id"),
                       range(1, len(membershipList) + 1),
                       membershipList)
        Util.write_tsv(config.FILE_NAME_REGION_BORDERS,
                       ("region_id", "border_list"),
                       range(1, len(regionList) + 1),
                       regionList)


class CreateContours(MTimeMixin, luigi.Task):
    '''
    Creates the contours layer.
    '''
    def requires(self):
        return CreateCoordinates(), CreateContinents()

    def output(self):
        return luigi.LocalTarget(config.FILE_NAME_CONTOUR_DATA),

    def run(self):
        xyCoords = Util.read_features(config.FILE_NAME_ARTICLE_COORDINATES, config.FILE_NAME_NUMBERED_CLUSTERS)
        contour = Contours.ContourCreator()
        contour.buildContours(list(xyCoords.values()))
        contour.makeContourFeatureCollection(config.FILE_NAME_CONTOUR_DATA)


class CreateMap(MTimeMixin, luigi.Task):
    '''
    Creates the mapnik map.xml configuration file and renders png and svg
    images of the map. THIS IS UNTESTED!
    '''
    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_MAP),
            luigi.LocalTarget(config.FILE_NAME_IMGNAME + '.png'),
            luigi.LocalTarget(config.FILE_NAME_IMGNAME + '.svg')
        )

    def requires(self):
        return (
            CreateContours(),
            CreateCoordinates(),
            CreateContinents()
        )

    def run(self):
        regionClusters = Util.read_features(config.FILE_NAME_REGION_CLUSTERS)
        regionIds = sorted(set(region['cluster_id'] for region in regionClusters.values()))
        ms = MapStyler.MapStyler()
        ms.makeMap(config.FILE_NAME_CONTOUR_DATA, config.FILE_NAME_COUNTRIES, regionIds)
        ms.saveMapXml(config.FILE_NAME_COUNTRIES, config.FILE_NAME_MAP)
        ms.saveImage(config.FILE_NAME_MAP, config.FILE_NAME_IMGNAME + ".png")
        ms.saveImage(config.FILE_NAME_MAP, config.FILE_NAME_IMGNAME + ".svg")
