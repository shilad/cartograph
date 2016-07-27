import luigi
import logging
import cartograph
from cartograph import Config
import cartograph.Coordinates
import cartograph.LuigiUtils
import cartograph.PreReqs
import cartograph.Popularity
from cartograph import PopularityLabelSizer
from cartograph.CalculateZooms import ZoomLabeler
from cartograph import Colors
from cartograph import Utils
from cartograph import Contour
from cartograph.Denoiser import Denoise
from cartograph import MapStyler
from cartograph.BorderGeoJSONWriter import CreateContinents
from cartograph.ZoomGeoJSONWriter import ZoomGeoJSONWriter
from cartograph.Labels import Labels
from cartograph.Regions import MakeRegions
from time import time
import numpy as np
from cartograph.LuigiUtils import LoadGeoJsonTask, TimestampedLocalTarget, MTimeMixin

RUN_TIME = time()

logger = logging.getLogger('workload')
logger.setLevel(logging.INFO)


class ColorsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Colors.__file__))


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.MapStyler.__file__))


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


class CreateStates(MTimeMixin, luigi.Task):
    '''
    Create states within regions
    '''
    def requires(self):
        return(Denoise(),
               CreateContinents(),
               Contour.CreateContours())
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
                PopularityLabelSizer.PercentilePopularityIdentifier(),
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
        return Contour.CreateContours(), PGLoaderCode()


class LoadContoursCentroid(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
                                 config,
                                 'contourscentroid',
                                 config.get('MapData', 'centroid_contours_geojson'))

    def requires(self):
        return Contour.CreateContours(), PGLoaderCode()


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
