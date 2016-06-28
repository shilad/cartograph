import luigi
import os
from cartograph import Config
from cartograph import Util
from cartograph import Contours
from cartograph import Denoiser
from cartograph import MapStyler
from cartograph.BorderFactory import BorderFactory
from cartograph.BorderGeoJSONWriter import BorderGeoJSONWriter
from cartograph.TopTitlesGeoJSONWriter import TopTitlesGeoJSONWriter
from cartograph.Labels import Labels
from tsne import bh_sne
import numpy as np
from sklearn.cluster import KMeans


config = Config.BAD_GET_CONFIG()  # To be removed


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


# ====================================================================
# Read in codebase as external dependencies to automate a rerun of any
# code changed without having to do a manual invalidation
# NOTE: Any new .py files that will run *must* go here for automation
# ====================================================================

class ContourCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/Contours.py"))


class DenoiserCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/Denoiser.py"))


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/MapStyler.py"))


class BorderFactoryCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/BorderFactory.py"))


class BorderGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/BorderGeoJSONWriter.py"))


class TopTitlesGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/TopTitlesGeoJSONWriter.py"))


class LabelsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget("./cartograph/Labels.py"))


# ====================================================================
# Clean up raw wikibrain data for uniform data structure manipulation
# ====================================================================


class WikiBrainData(luigi.ExternalTask):
    '''
    Ensure that all external files produced by WikiBrain exist in
    the correct directory.
    '''
    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_WIKIBRAIN_NAMES),
                luigi.LocalTarget(config.FILE_NAME_WIKIBRAIN_VECS))


class LabelNames(luigi.ExternalTask):
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''
    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_REGION_NAMES))


class ArticlePopularity(luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_POPULARITY))


class WikiBrainNumbering(MTimeMixin, luigi.Task):
    '''
    Number the name and vector output of WikiBrain files so that each
    article has a unique id corrosponding to all of its data for future
    use of any subset of features of interest
    '''
    def requires(self):
        return WikiBrainData()

    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_NUMBERED_VECS),
                luigi.LocalTarget(config.FILE_NAME_NUMBERED_NAMES))

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


# ====================================================================
# Data Training and Analysis Stage
# ====================================================================


class PopularityLabeler(MTimeMixin, luigi.Task):
    '''
    Generate a tsv that matches Wikibrain popularity count to a unique
    article ID for later compatibility with Util.read_features()
    '''
    def requires(self):
        return (WikiBrainNumbering(),
                ArticlePopularity())

    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_NUMBERED_POPULARITY))

    def run(self):
        featureDict = Util.read_features(config.FILE_NAME_NUMBERED_NAMES)
        idList = list(featureDict.keys())

        nameDict = {}
        with open(config.FILE_NAME_POPULARITY) as popularity:
            lines = popularity.readlines()
            for line in lines:
                lineAr = line.split("\t")
                name = lineAr[0]
                pop = lineAr[1][:-1]
                nameDict[name] = pop

        popularityList = []
        for featureID in idList:
            name = featureDict[featureID]["name"]
            popularityList.append(nameDict[name])

        Util.write_tsv(config.FILE_NAME_NUMBERED_POPULARITY,
                       ("id", "popularity"),
                       idList, popularityList)


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
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        labels = list(KMeans(config.NUM_CLUSTERS,
                             random_state=42).fit(vectors).labels_)
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
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
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
        return (RegionClustering(),
                CreateCoordinates(),
                DenoiserCode())

    def run(self):
        featureDict = Util.read_features(config.FILE_NAME_ARTICLE_COORDINATES,
                                         config.FILE_NAME_NUMBERED_CLUSTERS)
        featureIDs = list(featureDict.keys())
        x = [float(featureDict[fID]["x"]) for fID in featureIDs]
        y = [float(featureDict[fID]["y"]) for fID in featureIDs]
        c = [int(featureDict[fID]["cluster"]) for fID in featureIDs]

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


# ====================================================================
# Map File and Image (for visual check) Stage
# ====================================================================


class CreateContinents(MTimeMixin, luigi.Task):
    '''
    Use BorderFactory to define edges of continent polygons based on
    vornoi tesselations of both article and waterpoints storing
    article clusters as the points of their exterior edge
    '''
    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_COUNTRIES),
            luigi.LocalTarget(config.FILE_NAME_REGION_CLUSTERS),
            luigi.LocalTarget(config.FILE_NAME_REGION_BORDERS)
        )

    def requires(self):
        return (LabelNames(),
                BorderGeoJSONWriterCode(),
                Denoise(),
                BorderFactoryCode())

    def decomposeBorders(self, clusterDict):
        '''
        Break down clusters into every region that comprises the whole
        and save for later possible data manipulation
        TODO: Extract interior ports as well as borders
        '''
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
        clustList = list(clusterDict.values())
        regionList, membershipList = self.decomposeBorders(clusterDict)

        BorderGeoJSONWriter(clustList).writeToFile(config.FILE_NAME_COUNTRIES)
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
    Make contours based on density of points inside the map
    Generated as geojson data for later use inside map.xml
    '''
    def requires(self):
        return (CreateCoordinates(),
                ContourCode(), 
                CreateContinents())

    def output(self):
        return luigi.LocalTarget(config.FILE_NAME_CONTOUR_DATA)

    def run(self):
        xyCoords = Util.read_features(config.FILE_NAME_ARTICLE_COORDINATES, config.FILE_NAME_NUMBERED_CLUSTERS)
        contour = Contours.ContourCreator()
        contour.buildContours(list(xyCoords.values()))
        contour.makeContourFeatureCollection(config.FILE_NAME_CONTOUR_DATA)


class CreateLabels(MTimeMixin, luigi.Task):
    '''
    Write the top 100 most popular articles to file for relative zoom
    Generated as geojson data for use inside map.xml
    '''
    def requires(self):
        return (PopularityLabeler(),
                CreateCoordinates(),
                TopTitlesGeoJSONWriterCode())

    def output(self):
        return luigi.LocalTarget(config.FILE_NAME_TOP_TITLES)

    def run(self):
        titleLabels = TopTitlesGeoJSONWriter(100)
        titleLabels.generateJSONFeature(config.FILE_NAME_TOP_TITLES)


class CreateMapXml(MTimeMixin, luigi.Task):
    '''
    Creates the mapnik map.xml configuration file and renders png and svg
    images of the map for visual reference to make sure code excuted properly.
    Map png and svg can be found in ./data/images
    '''
    def output(self):
        return (
            luigi.LocalTarget(config.FILE_NAME_MAP))

    def requires(self):
        return (
            CreateContours(),
            CreateCoordinates(),
            CreateContinents(),
            MapStylerCode()
        )

    def run(self):
        regionClusters = Util.read_features(config.FILE_NAME_REGION_CLUSTERS)
        regionIds = sorted(set(int(region['cluster_id']) for region in regionClusters.values()))
        regionIds = map(str, regionIds)
        ms = MapStyler.MapStyler()
        ms.makeMap(config.FILE_NAME_CONTOUR_DATA,
                   config.FILE_NAME_COUNTRIES,
                   regionIds)
        ms.saveMapXml(config.FILE_NAME_COUNTRIES, config.FILE_NAME_MAP)
        ms.saveImage(config.FILE_NAME_MAP, config.FILE_NAME_IMGNAME + ".png")
        ms.saveImage(config.FILE_NAME_MAP, config.FILE_NAME_IMGNAME + ".svg")


class LabelMap(MTimeMixin, luigi.Task):
    '''
    Mapnik's text renderer is unsupported by the wrapper we're using so
    instead, labels must be written directly to the xml file to be rendered
    '''
    def requires(self):
        return (CreateMapXml(),
                CreateLabels(),
                CreateContinents(),
                LabelsCode())

    def output(self):
        return (luigi.LocalTarget(config.FILE_NAME_MAP))

    def run(self):
        label = Labels(config.FILE_NAME_MAP, config.FILE_NAME_COUNTRIES)
        label.writeLabelsXml('[labels]', 'interior',
                             maxScale='559082264', minScale='17471321')

        titleLabels = Labels(config.FILE_NAME_MAP, config.FILE_NAME_TOP_TITLES)
        titleLabels.writeShieldXml('[titleLabel]', 'point',
                                   imgFile=config.FILE_NAME_IMGDOT,
                                   minScale='1091958', maxScale='17471321'
                                   )


class RenderMap(MTimeMixin, luigi.Task):
    '''
    Write the final product xml of all our data manipulations to an image file
    to ensure that everything excuted as it should
    '''
    def requires(self):
        return (CreateMapXml(),
                LabelMap(),
                MapStylerCode())

    def output(self):
        return(
            luigi.LocalTarget(config.FILE_NAME_IMGNAME + '.png'),
            luigi.LocalTarget(config.FILE_NAME_IMGNAME + '.svg'))

    def run(self):
        ms = MapStyler.MapStyler()
        ms.saveImage(config.FILE_NAME_MAP, config.FILE_NAME_IMGNAME + ".png")
        ms.saveImage(config.FILE_NAME_MAP, config.FILE_NAME_IMGNAME + ".svg")
