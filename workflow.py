import luigi
import os

import cartograph

from cartograph import Config
from cartograph import Util
from cartograph import DensityContours
from cartograph import CentroidContours
from cartograph import Denoiser
from cartograph import MapStyler
from cartograph.BorderFactory.BorderBuilder import BorderBuilder
from cartograph.BorderGeoJSONWriter import BorderGeoJSONWriter
from cartograph.TopTitlesGeoJSONWriter import TopTitlesGeoJSONWriter
from cartograph.ZoomGeoJSONWriter import ZoomGeoJSONWriter
from cartograph.Labels import Labels
from cartograph.Config import initConf, COLORWHEEL
from cartograph.CalculateZooms import CalculateZooms
from cartograph.Interpolater import Interpolater
from tsne import bh_sne
from time import time
import numpy as np
from sklearn.cluster import KMeans
from cartograph.PGLoader import LoadGeoJsonTask, TimestampedPostgresTarget


config = initConf("conf.txt")  # To be removed


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
            return int(os.path.getmtime(path))

        if not all(os.path.exists(out.path) for out in to_list(self.output())):
            return False

        self_mtime = min(mtime(out.path) for out in to_list(self.output()))

        for el in to_list(self.requires()):
            if not el.complete():
                return False
            for output in to_list(el.output()):
                if isinstance(output, TimestampedPostgresTarget):
                    if output.last_mtime() > self_mtime:
                        return False
                else:
                    if mtime(output.path) > self_mtime:
                        return False
        return True


# ====================================================================
# Read in codebase as external dependencies to automate a rerun of any
# code changed without having to do a manual invalidation
# NOTE: Any new .py files that will run *must* go here for automation
# ====================================================================

class DensityContourCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.DensityContours.__file__))


class CentroidContourCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.CentroidContours.__file__))


class DenoiserCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.Denoiser.__file__))


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.MapStyler.__file__))


class BorderFactoryCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.BorderFactory.BorderBuilder.__file__))


class BorderGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.BorderGeoJSONWriter.__file__))


class TopTitlesGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.TopTitlesGeoJSONWriter.__file__))


class LabelsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.Labels.__file__))


class CalculateZoomsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.CalculateZooms.__file__))


class ZoomGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(luigi.LocalTarget(cartograph.ZoomGeoJSONWriter.__file__))

class PGLoaderCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(cartograph.PGLoader.__file__))

class InterpolaterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(luigi.LocalTarget(cartograph.Interpolater.__file__))


# ====================================================================
# Clean up raw wikibrain data for uniform data structure manipulation
# ====================================================================


class LabelNames(luigi.ExternalTask):
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''
    def output(self):
        return (luigi.LocalTarget(config.get("ExternalFiles", "region_names")))


class ArticlePopularity(luigi.ExternalTask):
    def output(self):
        return (luigi.LocalTarget(config.get("ExternalFiles", "popularity")))


class WikiBrainNumbering(MTimeMixin, luigi.ExternalTask):
    '''
    Number the name and vector output of WikiBrain files so that each
    article has a unique id corrosponding to all of its data for future
    use of any subset of features of interest
    '''

    def output(self):
        return (luigi.LocalTarget(config.get("ExternalFiles",
                                             "vecs_with_id")),
                luigi.LocalTarget(config.get("ExternalFiles",
                                             "names_with_id")))


class InterpolateNewPoints(MTimeMixin, luigi.Task):
    def requires(self):
        return (InterpolaterCode(),
                CreateCoordinates())

    def output(self):
        return (luigi.LocalTarget(config.get("PostprocessingFiles",
                                             "vecs_with_id")),
                luigi.LocalTarget(config.get("PostprocessingFiles",
                                             "names_with_id")),
                luigi.LocalTarget(config.get("PostprocessingFiles",
                                             "article_coordinates")),
                luigi.LocalTarget(config.get("PostprocessingFiles", 
                                             "popularity_with_id")))

    def updateConfig(self):
        if config.get("DEFAULT", "interpolateDir") != "none":
            newNames = config.get("InterpolateFiles", "new_names")
            newVecs = config.get("InterpolateFiles", "new_vecs")
            newCoords = config.get("InterpolateFiles", "new_coords")
            newPopularity = config.get("InterpolateFiles", "new_popularity")

        else: 
            newNames = config.get("ExternalFiles", "names_with_id")
            newVecs = config.get("ExternalFiles", "vecs_with_id")
            newCoords = config.get("PreprocessingFiles", "article_coordinates")
            newPopularity = config.get("PreprocessingFiles", "popularity_with_id")
            now = (time(), time())
            os.utime(newNames, now)
            os.utime(newVecs, now)
            os.utime(newCoords, now)
            os.utime(newPopularity, now)

        config.set("PostprocessingFiles", "article_coordinates", newCoords)
        config.set("PostprocessingFiles", "vecs_with_id", newVecs)
        config.set("PostprocessingFiles", "names_with_id", newNames)
        config.set("PostprocessingFiles", "popularity_with_id", newPopularity)

    def run(self):
        if config.get("DEFAULT", "interpolateDir") != "none":
            print "Updating"
            embeddingDict = Util.read_features(config.get("ExternalFiles",
                                                          "vecs_with_id"),
                                               config.get("ExternalFiles",
                                                          "names_with_id"),
                                               config.get("PreprocessingFiles",
                                                          "article_coordinates"))
            interpolateDict = Util.read_features(config.get("InterpolateFiles",
                                                            "vecs"),
                                                config.get("InterpolateFiles",
                                                            "names"),
                                                config.get("InterpolateFiles",
                                                            "popularity"))
            interpolater = Interpolater(embeddingDict, interpolateDict, config)
            interpolater.interpolatePoints()
        else:
            print "not updating"
        self.updateConfig()
 

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
        return (luigi.LocalTarget(config.get("PreprocessingFiles",
                                             "popularity_with_id")))

    def run(self):
        featureDict = Util.read_features(config.get("ExternalFiles",
                                                    "names_with_id"))
        idList = list(featureDict.keys())

        nameDict = {}
        with open(config.get("ExternalFiles", "popularity")) as popularity:
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

        Util.write_tsv(config.get("PreprocessingFiles", "popularity_with_id"),
                       ("id", "popularity"),
                       idList, popularityList)


class PercentilePopularity(MTimeMixin, luigi.Task):
    '''
    Bins the popularity values by given percentiles then maps the values to
    the unique article ID.
    '''
    def requires(self):
        return (PopularityLabeler())

    def output(self):
        return (luigi.LocalTarget(config.get("PreprocessingFiles",
                                             "normalized_popularity")))

    def run(self):
        readPopularData = Util.read_tsv(config.get("PreprocessingFiles",
                                                   "popularity_with_id"))
        popularity = map(float, readPopularData['popularity'])
        index = map(int, readPopularData['id'])

        # totalSum = sum(popularity)
        # normPopularity = map(lambda x: float(x)/totalSum, popularity)


class RegionClustering(MTimeMixin, luigi.Task):
    '''
    Run KMeans to cluster article points into specific continents.
    Seed is set at 42 to make sure that when run against labeling
    algorithm clusters numbers consistantly refer to the same entity
    '''
    def output(self):
        return luigi.LocalTarget(config.get("PreprocessingFiles",
                                            "clusters_with_id"))

    def requires(self):
        return (InterpolateNewPoints())

    def run(self):
        featureDict = Util.read_features(config.get("PostprocessingFiles",
                                                    "vecs_with_id"))
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        labels = list(KMeans(config.getint("PreprocessingConstants",
                                           "num_clusters"),
                             random_state=42).fit(vectors).labels_)

        Util.write_tsv(config.get("PreprocessingFiles", "clusters_with_id"),
                       ("index", "cluster"), keys, labels)


class CreateEmbedding(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes
    '''
    def output(self):
        return luigi.LocalTarget(config.get("ExternalFiles",
                                            "article_embedding"))

    def requires(self):
        return WikiBrainNumbering()

    def run(self):
        featureDict = Util.read_features(config.get("ExternalFiles",
                                                    "vecs_with_id"))
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        out = bh_sne(vectors,
                     pca_d=None,
                     theta=config.getfloat("PreprocessingConstants", "tsne_theta"))
        X, Y = list(out[:, 0]), list(out[:, 1])
        Util.write_tsv(config.get("ExternalFiles", "article_embedding"),
                       ("index", "x", "y"), keys, X, Y)


class CreateCoordinates(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes
    '''
    def output(self):
        return luigi.LocalTarget(config.get("PreprocessingFiles",
                                            "article_coordinates"))

    def requires(self):
        return CreateEmbedding()

    def run(self):
        points = Util.read_features(config.get("ExternalFiles",
                                               "article_embedding"))
        keys = list(points.keys())
        X = [float(points[k]['x']) for k in keys]
        Y = [float(points[k]['y']) for k in keys]
        maxVal = max(abs(v) for v in X + Y)
        scaling = config.getint("MapConstants", "max_coordinate") / maxVal
        X = [x * scaling for x in X]
        Y = [y * scaling for y in Y]
        Util.write_tsv(config.get("PreprocessingFiles",
                                  "article_coordinates"),
                       ("index", "x", "y"), keys, X, Y)


class ZoomLabeler(MTimeMixin, luigi.Task):
    '''
    Calculates a starting zoom level for every article point in the data,
    i.e. determines when each article label should appear.
    '''
    def output(self):
        return luigi.LocalTarget(config.get("PreprocessingFiles",
                                            "zoom_with_id"))

    def requires(self):
        return (RegionClustering(),
                CalculateZoomsCode(),
                CreateCoordinates(),
                PopularityLabeler())

    def run(self):
        feats = Util.read_features(config.get("PostprocessingFiles",
                                              "popularity_with_id"),
                                   config.get("PostprocessingFiles",
                                              "article_coordinates"),
                                   config.get("PreprocessingFiles",
                                              "clusters_with_id"))

        zoom = CalculateZooms(feats,
                              config.getint("MapConstants", "max_coordinate"),
                              config.getint("PreprocessingConstants", "num_clusters"))
        numberedZoomDict = zoom.simulateZoom(config.getint("MapConstants", "max_zoom"))
        keys = list(numberedZoomDict.keys())
        zoomValue = list(numberedZoomDict.values())

        Util.write_tsv(config.get("PreprocessingFiles", "zoom_with_id"),
                       ("index", "maxZoom"), keys, zoomValue)


class Denoise(MTimeMixin, luigi.Task):
    '''
    Remove outlier points and set water level for legibility in reading
    and more coherent contintent boundary lines
    '''
    def output(self):
        return (
            luigi.LocalTarget(config.get("PreprocessingFiles",
                                         "denoised_with_id")),
            luigi.LocalTarget(config.get("PreprocessingFiles",
                                         "clusters_with_water")),
            luigi.LocalTarget(config.get("PreprocessingFiles",
                                         "coordinates_with_water"))
        )

    def requires(self):
        return (RegionClustering(),
                CreateCoordinates(),
                InterpolateNewPoints(),
                DenoiserCode())

    def run(self):
        featureDict = Util.read_features(config.get("PostprocessingFiles",
                                                    "article_coordinates"),
                                         config.get("PreprocessingFiles",
                                                    "clusters_with_id"))
        featureIDs = list(featureDict.keys())
        x = [float(featureDict[fID]["x"]) for fID in featureIDs]
        y = [float(featureDict[fID]["y"]) for fID in featureIDs]
        c = [int(featureDict[fID]["cluster"]) for fID in featureIDs]

        denoiser = Denoiser.Denoiser(x, y, c,
                                     config.getfloat("PreprocessingConstants",
                                                     "water_level"))
        keepBooleans, waterX, waterY, waterCluster = denoiser.denoise()

        for x in range(len(waterX) - len(featureIDs)):
            featureIDs.append("w" + str(x))

        Util.write_tsv(config.get("PreprocessingFiles",
                                  "denoised_with_id"),
                       ("index", "keep"),
                       featureIDs, keepBooleans)

        Util.write_tsv(config.get("PreprocessingFiles",
                                  "coordinates_with_water"),
                       ("index", "x", "y"), featureIDs, waterX, waterY)
        Util.write_tsv(config.get("PreprocessingFiles", "clusters_with_water"),
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
            luigi.LocalTarget(config.get("MapData", "countries_geojson")),
            luigi.LocalTarget(config.get("MapData", "clusters_with_region_id")),
            luigi.LocalTarget(config.get("MapData", "borders_with_region_id")))

    def requires(self):
        return (LabelNames(),
                BorderGeoJSONWriterCode(),
                BorderFactoryCode(),
                RegionClustering(),
                Denoise())

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
        clusterDict = BorderBuilder(config).build()
        clustList = list(clusterDict.values())
        regionList, membershipList = self.decomposeBorders(clusterDict)

        regionFile = config.get("ExternalFiles", "region_names")
        BorderGeoJSONWriter(clustList, regionFile).writeToFile(config.get("MapData", "countries_geojson"))
        Util.write_tsv(config.get("MapData", "clusters_with_region_id"),
                       ("region_id", "cluster_id"),
                       range(1, len(membershipList) + 1),
                       membershipList)
        Util.write_tsv(config.get("MapData", "borders_with_region_id"),
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
                CentroidContourCode(),
                DensityContourCode(),
                CreateContinents())

    def output(self):
        return luigi.LocalTarget(config.get("MapData", "contours_geojson"))

    def run(self):
        featuresDict = Util.read_features(config.get("PostprocessingFiles",
                                                     "article_coordinates"),
                                          config.get("PreprocessingFiles",
                                                     "clusters_with_id"),
                                          config.get("PreprocessingFiles",
                                                     "denoised_with_id"),
                                          config.get("PostprocessingFiles",
                                                     "vecs_with_id"))
        for key in featuresDict.keys():
            if key[0] == "w":
                del featuresDict[key]

        numClusters = config.getint("PreprocessingConstants", "num_clusters")
        numContours = config.getint('PreprocessingConstants', 'num_contours')
        writeFile = config.get("MapData", "countries_geojson")

        centroidContour = CentroidContours.ContourCreator(numClusters)
        centroidContour.buildContours(featuresDict, writeFile, numContours)
        centroidContour.makeContourFeatureCollection(config.get("MapData", "contours_geojson"))

        densityContour = DensityContours.ContourCreator(numClusters)
        densityContour.buildContours(featuresDict, writeFile, numContours)
        densityContour.makeContourFeatureCollection(config.get("MapData", "contours_geojson"))


class CreateLabelsFromZoom(MTimeMixin, luigi.Task):
    '''
    Generates geojson data for relative zoom labelling in map.xml
    '''
    def output(self):
        return luigi.LocalTarget(config.get("MapData", "title_by_zoom"))

    def requires(self):
        return (ZoomLabeler())

    def run(self):
        featureDict = Util.read_features(
            config.get("PreprocessingFiles", "zoom_with_id"),
            config.get("PostprocessingFiles", "article_coordinates"),
            config.get("PostprocessingFiles", "popularity_with_id"),
            config.get("PostprocessingFiles", "names_with_id"))
        titlesByZoom = ZoomGeoJSONWriter(featureDict)
        titlesByZoom.generateZoomJSONFeature(config.get("MapData", "title_by_zoom"))


class CreateTopLabels(MTimeMixin, luigi.Task):
    '''
    Write the top 100 most popular articles to file for relative zoom
    Generated as geojson data for use inside map.xml
    '''
    def requires(self):
        return (PopularityLabeler(),
                CreateCoordinates(),
                RegionClustering(),
                TopTitlesGeoJSONWriterCode())

    def output(self):
        return luigi.LocalTarget(config.get("MapData", "top_titles"))

    def run(self):
        titleLabels = TopTitlesGeoJSONWriter(9000)
        titleLabels.generateJSONFeature(config.get("MapData", "top_titles"))

class LoadContours(LoadGeoJsonTask):
    def __init__(self):
        LoadGeoJsonTask.__init__(self, 
            config, 
            'contours', 
            config.get('MapData', 'contours_geojson')
        )

    def requires(self):
        return CreateContours(), PGLoaderCode()


class LoadCoordinates(LoadGeoJsonTask):
    def __init__(self):
        LoadGeoJsonTask.__init__(self, 
            config, 
            'coordinates', 
            config.get('MapData', 'title_by_zoom')
        )

    def requires(self):
        return CreateCoordinates(), PGLoaderCode()


class LoadCountries(LoadGeoJsonTask):
    def __init__(self):
        LoadGeoJsonTask.__init__(self,
            config, 'countries',
            config.get('MapData', 'countries_geojson')
        )

    def requires(self):
        return CreateContinents(), PGLoaderCode()


class CreateMapXml(MTimeMixin, luigi.Task):
    '''
    Creates the mapnik map.xml configuration file and renders png and svg
    images of the map for visual reference to make sure code excuted properly.
    Map png and svg can be found in ./data/images
    '''
    def output(self):
        return (
            luigi.LocalTarget(config.get("MapOutput", "map_file")))

    def requires(self):
        return (
            LoadContours(),
            LoadCoordinates(),
            LoadCountries(),
            MapStylerCode()
        )

    def run(self):
        regionClusters = Util.read_features(config.get("MapData", "clusters_with_region_id"))
        regionIds = sorted(set(int(region['cluster_id']) for region in regionClusters.values()))
        regionIds = map(str, regionIds)
        colorwheel = COLORWHEEL
        ms = MapStyler.MapStyler(config, colorwheel)
        mapfile = config.get("MapOutput", "map_file")
        imgfile = config.get("MapOutput", "img_src_name")

        ms.makeMap(config.get("MapData", "contours_geojson"),
                   config.get("MapData", "countries_geojson"),
                   regionIds)
        ms.saveMapXml(config.get("MapData", "countries_geojson"),
                      mapfile)
        ms.saveImage(mapfile, imgfile + ".png")
        ms.saveImage(mapfile, imgfile + ".svg")


class LabelMapUsingZoom(MTimeMixin, luigi.Task):
    '''
    Adding the labels directly into the xml file for map rendering.
    Labels are added to appear based on a grid based zoom calculation in
    the CalculateZooms.py
    '''
    def output(self):
        return (luigi.LocalTarget(config.get("MapOutput", "map_file")))

    def requires(self):
        return (CreateMapXml(),
                CreateLabelsFromZoom(),
                CreateContinents(),
                LabelsCode(),
                CalculateZoomsCode(),
                ZoomGeoJSONWriterCode()
                )

    def run(self):
        labelClust = Labels(config, config.get("MapOutput", "map_file"),
                            'countries', config.get("MapData", "scale_dimensions"))
        maxScaleClust = labelClust.getScaleDenominator(0)
        minScaleClust = labelClust.getScaleDenominator(5)

        labelClust.writeLabelsXml('[labels]', 'interior',
                                  minScale=minScaleClust,
                                  maxScale=maxScaleClust)

        zoomValues = set()
        zoomValueData = Util.read_features(config.get("PreprocessingFiles",
                                                      "zoom_with_id"))
        for zoomInfo in list(zoomValueData.values()):
            zoomValues.add(zoomInfo['maxZoom'])

        labelCities = Labels(config, config.get("MapOutput", "map_file"),
                             'coordinates', config.get("MapData", "scale_dimensions"))
        labelCities.writeLabelsByZoomToXml('[citylabel]', 'point',
                                           config.getint("MapConstants", "max_zoom"),
                                           imgFile=config.get("MapResources",
                                                              "img_dot"))


class RenderMap(MTimeMixin, luigi.Task):
    '''
    Write the final product xml of all our data manipulations to an image file
    to ensure that everything excuted as it should
    '''
    def requires(self):
        return (CreateMapXml(),
                LabelMapUsingZoom(),
                MapStylerCode())

    def output(self):
        return(
            luigi.LocalTarget(config.get("MapOutput",
                                         "img_src_name") + '.png'),
            luigi.LocalTarget(config.get("MapOutput",
                                         "img_src_name") + '.svg'))

    def run(self):
        colorwheel = COLORWHEEL
        ms = MapStyler.MapStyler(config, COLORWHEEL)
        ms.saveImage(config.get("MapOutput", "map_file"),
                     config.get("MapOutput", "img_src_name") + ".png")
        ms.saveImage(config.get("MapOutput", "map_file"),
                     config.get("MapOutput", "img_src_name") + ".svg")
