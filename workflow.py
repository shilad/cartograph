import luigi
import matplotlib


matplotlib.use('Agg')
import logging
import cartograph
from cartograph import Config

logger = logging.getLogger('workload')
logger.setLevel(logging.INFO)

import cartograph.Coordinates
import cartograph.LuigiUtils
import cartograph.PreReqs
import cartograph.Popularity
from cartograph.CalculateZooms import ZoomLabeler
from cartograph import Colors
from cartograph import Utils
from cartograph import Contour
from cartograph import Denoiser
from cartograph import MapStyler
from cartograph.borders.BorderBuilder import BorderBuilder
from cartograph.borders import BorderProcessor, Noiser, Vertex, VoronoiWrapper
from cartograph.BorderGeoJSONWriter import BorderGeoJSONWriter
from cartograph.TopTitlesGeoJSONWriter import TopTitlesGeoJSONWriter
from cartograph.ZoomGeoJSONWriter import ZoomGeoJSONWriter
from cartograph.Labels import Labels
from cartograph.CalculateZooms import CalculateZooms
from cartograph.PopularityLabelSizer import PopularityLabelSizer
from cartograph.Regions import MakeRegions, MakeSampleRegions
from collections import defaultdict
from time import time
import numpy as np
from cartograph.LuigiUtils import LoadGeoJsonTask, TimestampedLocalTarget, MTimeMixin, getSampleIds

RUN_TIME = time()


# ====================================================================
# Read in codebase as external dependencies to automate a rerun of any
# code changed without having to do a manual invalidation
# NOTE: Any new .py files that will run *must* go here for automation
# ====================================================================

class ContourCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Contour.__file__))


class ColorsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Colors.__file__))


class DenoiserCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Denoiser.__file__))


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.MapStyler.__file__))


class BorderFactoryCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.borders.BorderBuilder.__file__),
                TimestampedLocalTarget(cartograph.borders.BorderProcessor.__file__),
                TimestampedLocalTarget(cartograph.borders.Noiser.__file__),
                TimestampedLocalTarget(cartograph.borders.Vertex.__file__),
                TimestampedLocalTarget(cartograph.borders.VoronoiWrapper.__file__))


class BorderGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.BorderGeoJSONWriter.__file__))


class TopTitlesGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.TopTitlesGeoJSONWriter.__file__))


class LabelsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Labels.__file__))


class ZoomGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(cartograph.ZoomGeoJSONWriter.__file__))


class PGLoaderCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.LuigiUtils.__file__))


# ====================================================================
# Clean up raw wikibrain data for uniform data structure manipulation
# ====================================================================

# ====================================================================
# Data Training and Analysis Stage
# ====================================================================


class Denoise(MTimeMixin, luigi.Task):
    '''
    Remove outlier points and set water level for legibility in reading
    and more coherent contintent boundary lines
    '''
    def output(self):
        config = Config.get()
        return (
            TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                         "denoised_with_id")),
            TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                         "clusters_with_water")),
            TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                         "coordinates_with_water"))
        )

    def requires(self):
        return (MakeRegions(),
                cartograph.Coordinates.CreateSampleCoordinates(),
                DenoiserCode())

    def run(self):
        config = Config.get()
        featureDict = Utils.read_features(config.getSample("GeneratedFiles",
                                                    "article_coordinates"),
                                          config.getSample("GeneratedFiles",
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

        Utils.write_tsv(config.getSample("GeneratedFiles",
                                  "denoised_with_id"),
                        ("index", "keep"),
                        featureIDs, keepBooleans)

        Utils.write_tsv(config.getSample("GeneratedFiles",
                                  "coordinates_with_water"),
                        ("index", "x", "y"), featureIDs, waterX, waterY)
        Utils.write_tsv(config.getSample("GeneratedFiles", "clusters_with_water"),
                        ("index", "cluster"), featureIDs, waterCluster)


# ====================================================================
# Map File and Image (for visual check) Stage
# ====================================================================


class CreateContinents(MTimeMixin, luigi.Task):
    '''
    Use BorderFactory to define edges of continent polygons based on
    voronoi tesselations of both article and waterpoints storing
    article clusters as the points of their exterior edge
    '''
    def output(self):
        config = Config.get()
        return (
            TimestampedLocalTarget(config.get("MapData", "countries_geojson")),
            TimestampedLocalTarget(config.get("GeneratedFiles", "country_borders")),
            TimestampedLocalTarget(config.get("MapData", "clusters_with_region_id")),
            TimestampedLocalTarget(config.get("MapData", "borders_with_region_id")))

    def requires(self):
        return (cartograph.PreReqs.LabelNames(),
                cartograph.Coordinates.CreateSampleCoordinates(),
                BorderGeoJSONWriterCode(),
                BorderFactoryCode(),
                MakeSampleRegions(),
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
        config = Config.get()
        clusterDict = BorderBuilder(config).build()
        clustList = [list(clusterDict[x]) for x in list(clusterDict.keys())]
        regionList, membershipList = self.decomposeBorders(clusterDict)
        regionFile = config.get("ExternalFiles", "region_names")
        BorderGeoJSONWriter(clustList, regionFile).writeToFile(config.get("MapData", "countries_geojson"))
        Utils.write_tsv(config.get("MapData", "clusters_with_region_id"),
                        ("region_id", "cluster_id"),
                        range(1, len(membershipList) + 1),
                        membershipList)
        Utils.write_tsv(config.get("MapData", "borders_with_region_id"),
                        ("region_id", "border_list"),
                        range(1, len(regionList) + 1),
                        regionList)
        Utils.write_tsv(config.get("GeneratedFiles", "country_borders"),
                        ("cluster_id", "border_list"),
                        range(len(clustList)),
                        clustList)


class CreateContours(MTimeMixin, luigi.Task):
    '''
    Make contours based on density of points inside the map
    Generated as geojson data for later use inside map.xml
    '''
    def requires(self):
        config = Config.get()
        return (cartograph.Coordinates.CreateSampleCoordinates(),
                cartograph.Popularity.SampleCreator(config.get("ExternalFiles", "vecs_with_id")),
                ContourCode(),
                CreateContinents(),
                MakeRegions())

    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("MapData", "centroid_contours_geojson")),
                TimestampedLocalTarget(config.get("MapData", "density_contours_geojson")))



    def run(self):
        config = Config.get()
        featuresDict = Utils.read_features(config.getSample("GeneratedFiles",
                                                     "article_coordinates"),
                                           config.getSample("GeneratedFiles",
                                                     "clusters_with_id"),
                                           config.getSample("GeneratedFiles",
                                                     "denoised_with_id"),
                                           config.getSample("ExternalFiles",
                                                     "vecs_with_id"))
        for key in featuresDict.keys():
            if key[0] == "w":
                del featuresDict[key]


        numClusters = config.getint("PreprocessingConstants", "num_clusters")
        numContours = config.getint('PreprocessingConstants', 'num_contours')

        countryBorders = config.get("MapData", "countries_geojson")

        contour = Contour.ContourCreator(numClusters)
        contour.buildContours(featuresDict, countryBorders)
        contour.makeDensityContourFeatureCollection(config.get("MapData", "density_contours_geojson"))
        contour.makeCentroidContourFeatureCollection(config.get("MapData", "centroid_contours_geojson"))


class CreateStates(MTimeMixin, luigi.Task):
    '''
    Create states within regions
    '''
    def requires(self):
        return(Denoise(),
               CreateContinents(),
               CreateContours())
    def output(self):
        ''' TODO - figure out what this is going to return'''
        config = Config.get()
        return TimestampedLocalTarget(config.FILE_NAME_STATE_CLUSTERS)
    def run(self):
        config = Config.get()
        #create dictionary of article ids to a dictionary with cluster numbers and vectors representing them
        articleDict = Utils.read_features(config.FILE_NAME_NUMBERED_CLUSTERS, config.FILE_NAME_NUMBERED_VECS)

        #loop through and grab all the points (dictionaries) in each cluster that match the current cluster number (i), write the keys to a list
        for i in range(0, config.NUM_CLUSTERS):
            keys = []
            for article in articleDict:
                if int(articleDict[article]['cluster']) == i:
                    keys.append(article)
            #grab those articles' vectors from articleDict (thank you @ brooke for read_features, it is everything)
            vectors = np.array([articleDict[vID]['vector'] for vID in keys])

            #cluster vectors
            preStateLabels = list(KMeans(6,
                             random_state=42).fit(vectors).labels_)
            #append cluster number to cluster so that sub-clusters are of the form [larger][smaller] - eg cluster 4 has subclusters 40, 41, 42
            stateLabels = []
            for label in preStateLabels:
                newlabel = str(i) + str(label)
                stateLabels.append(newlabel)

            #also need to make a new utils method for append_tsv rather than write_tsv
            Utils.append_tsv(config.FILE_NAME_STATE_CLUSTERS,
                             ("index", "stateCluster"), keys, stateLabels)
        #CODE THUS FAR CREATES ALL SUBCLUSTERS, NOW YOU JUST HAVE TO FIGURE OUT HOW TO INTEGRATE THEM

        #ALSO HOW TO DETERMINE THE BEST # OF CLUSTERS FOR EACH SUBCLUSTER??? IT SEEMS LIKE THEY SHOULD VARY (MAYBE BASED ON # OF POINTS?)


        #then make sure those get borders created for them??
        #then create and color those polygons in xml

class CreateLabelsFromZoom(MTimeMixin, luigi.Task):
    '''
    Generates geojson data for relative zoom labelling in map.xml
    '''
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("MapData", "title_by_zoom"))

    def requires(self):
        return (ZoomLabeler(),
                cartograph.PopularityLabelSizer.PercentilePopularityIdentifier(),
                ZoomGeoJSONWriterCode())

    def run(self):
        config = Config.get()
        featureDict = Utils.read_features(
            config.get("GeneratedFiles", "zoom_with_id"),
            config.get("GeneratedFiles", "article_coordinates"),
            config.get("GeneratedFiles", "popularity_with_id"),
            config.get("ExternalFiles", "names_with_id"),
            config.get("GeneratedFiles", "percentile_popularity_with_id"),
            required=('x', 'y', 'popularity', 'name', 'maxZoom')
        )

        titlesByZoom = ZoomGeoJSONWriter(featureDict)
        titlesByZoom.generateZoomJSONFeature(config.get("MapData", "title_by_zoom"))


class LoadContoursDensity(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self, 
            config, 
            'contoursdensity',
            config.get('MapData', 'density_contours_geojson')
        )

    def requires(self):
        return CreateContours(), PGLoaderCode()


class LoadContoursCentroid(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
                                 config,
                                 'contourscentroid',
                                 config.get('MapData', 'centroid_contours_geojson'))

    def requires(self):
        return CreateContours(), PGLoaderCode()


class LoadCoordinates(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
            config,
            'coordinates',
            config.get('MapData', 'title_by_zoom')
        )

    def requires(self):
        return (
            cartograph.Coordinates.CreateFullCoordinates(),
            PGLoaderCode(),
            CreateLabelsFromZoom()
        )


class LoadCountries(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
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
        config = Config.get()
        return (
            TimestampedLocalTarget(config.get("MapOutput", "map_file_density")),
            TimestampedLocalTarget(config.get("MapOutput", "map_file_centroid")))

    def requires(self):
        return (
            LoadContoursDensity(),
            LoadContoursCentroid(),
            LoadCoordinates(),
            LoadCountries(),
            MapStylerCode(),
            ColorsCode()
        )

    def generateXml(self, contourDB, contourFile, mapfile):
        config = Config.get()
        regionClusters = Utils.read_features(config.get("MapData", "clusters_with_region_id"))
        regionIds = sorted(set(int(region['cluster_id']) for region in regionClusters.values()))
        regionIds = map(str, regionIds)
        countryBorders = Utils.read_features(config.get("GeneratedFiles", "country_borders"))
        colorFactory = Colors.ColorSelector(countryBorders, Config.getColorWheel())
        colors = colorFactory.optimalColoring()

        ms = MapStyler.MapStyler(config, colors)
        imgfile = config.get("MapOutput", "img_src_name")

        ms.addCustomFonts(config.get("MapResources","fontDir"))

        ms.makeMap(contourFile,
                   config.get("MapData", "countries_geojson"),
                   regionIds, contourDB)
        ms.saveMapXml(config.get("MapData", "countries_geojson"),
                      mapfile)
        ms.saveImage(mapfile, imgfile + ".png")
        ms.saveImage(mapfile, imgfile + ".svg")

    def run(self):
        config = Config.get()
        self.generateXml('contoursdensity',config.get("MapData", "density_contours_geojson"),
                         config.get("MapOutput", "map_file_density"))

        self.generateXml('contourscentroid',config.get("MapData", "centroid_contours_geojson"),
                         config.get("MapOutput", "map_file_centroid"))



class LabelMapUsingZoom(MTimeMixin, luigi.Task):
    '''
    Adding the labels directly into the xml file for map rendering.
    Labels are added to appear based on a grid based zoom calculation in
    the CalculateZooms.py
    '''
    def output(self):
        config = Config.get()
        return (
            TimestampedLocalTarget(config.get("MapOutput", "map_file_density")),
            TimestampedLocalTarget(config.get("MapOutput", "map_file_centroid")))

    def requires(self):
        return (CreateMapXml(),
                CreateLabelsFromZoom(),
                CreateContinents(),
                LabelsCode(),
                ZoomGeoJSONWriterCode()
                )

    def generateLabels(self, contourFile, mapFile):
        config = Config.get()
        zoomScaleData = Utils.read_zoom(config.get("MapData", "scale_dimensions"))

        labelClust = Labels(config, mapFile,
                            'countries', zoomScaleData)
        labelClust.addCustomFonts(config.get('MapResources', 'fontDir'))

        #For testing remove later.
        labelClust.addWaterXml()

        labelClust.writeLabelsXml('[labels]', 'interior',
                                  breakZoom=config.getint('MapConstants', 'first_zoom_label'),
                                  minScale=10,
                                  maxScale=0)

        labelCities = Labels(config, mapFile,
                             'coordinates',zoomScaleData)
        labelCities.writeLabelsByZoomToXml('[citylabel]', 'point',
                                           config.getint("MapConstants", "max_zoom"),
                                           imgFile=config.get("MapResources",
                                                              "img_dot"),
                                           numBins=config.getint("MapConstants",
                                                                "num_pop_bins"))


    def run(self):
        config = Config.get()
        self.generateLabels(config.get("MapData", "density_contours_geojson"),
                            config.get("MapOutput", "map_file_density"))
        self.generateLabels(config.get("MapData", "centroid_contours_geojson"),
                            config.get("MapOutput", "map_file_centroid"))


class RenderMap(MTimeMixin, luigi.Task):
    '''
    Write the final product xml of all our data manipulations to an image file
    to ensure that everything excuted as it should
    '''
    def requires(self):
        return (CreateMapXml(),
                LoadCoordinates(),
                LoadCountries(),
                LoadContoursDensity(),
                LoadContoursCentroid(),
                LabelMapUsingZoom(),
                MapStylerCode(),
                ColorsCode())

    def output(self):
        config = Config.get()
        return(
            TimestampedLocalTarget(config.get("MapOutput",
                                         "img_src_name") + '.png'),
            TimestampedLocalTarget(config.get("MapOutput",
                                         "img_src_name") + '.svg'))

    def run(self):
        config = Config.get()
        colorWheel = Config.getColorWheel()
        countryBorders = Utils.read_features(config.get("GeneratedFiles", "country_borders"))
        colorFactory = Colors.ColorSelector(countryBorders, colorWheel)
        colors = colorFactory.optimalColoring()
        ms = MapStyler.MapStyler(config, colors)
        ms = MapStyler.MapStyler(config, colorWheel)
        ms.saveImage(config.get("MapOutput", "map_file_density"),
                     config.get("MapOutput", "img_src_name") + ".png")
        ms.saveImage(config.get("MapOutput", "map_file_density"),
                     config.get("MapOutput", "img_src_name") + ".svg")
