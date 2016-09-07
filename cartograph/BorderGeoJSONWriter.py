from collections import defaultdict

import matplotlib

matplotlib.use("Agg")

import Config
import Utils
import luigi
import PreReqs
import Coordinates
import borders
import matplotlib.path as mplPath
from borders.BorderBuilder import BorderBuilder
from Denoiser import Denoise
from Regions import MakeSampleRegions
from geojson import Feature, FeatureCollection
from geojson import dumps, MultiPolygon
from LuigiUtils import MTimeMixin, TimestampedLocalTarget


class BorderFactoryCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(borders.BorderBuilder.__file__),
                TimestampedLocalTarget(borders.BorderProcessor.__file__),
                TimestampedLocalTarget(borders.Noiser.__file__),
                TimestampedLocalTarget(borders.Vertex.__file__),
                TimestampedLocalTarget(borders.VoronoiWrapper.__file__))


class BorderGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


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
        return (PreReqs.LabelNames(),
                Coordinates.CreateSampleCoordinates(),
                BorderGeoJSONWriterCode(),
                BorderFactoryCode(),
                MakeSampleRegions(),
                Denoise())

    def run(self):
        config = Config.get()
        clusterDict = BorderBuilder(config).build()
        keys = sorted(clusterDict.keys())

        # Flatten out region info into list of (regionId, clusterId, points)
        regionInfo = []
        for key in keys:
            for region in clusterDict[key]:
                regionInfo.append((
                    str(len(regionInfo) + 1),   # region id
                    str(key),                   # cluster id
                    region                      # points on exterior
                ))

        regionFile = config.get("ExternalFiles", "region_names")
        BorderGeoJSONWriter(regionInfo, regionFile).writeToFile(config.get("MapData", "countries_geojson"))

        # Mapping between regions and cluster ids
        Utils.write_tsv(config.get("MapData", "clusters_with_region_id"),
                        ("region_id", "cluster_id"),
                        [i[0] for i in regionInfo],
                        [i[1] for i in regionInfo])

        # Mapping beween
        Utils.write_tsv(config.get("MapData", "borders_with_region_id"),
                        ("region_id", "border_list"),
                        [i[0] for i in regionInfo],
                        [i[2] for i in regionInfo])
        Utils.write_tsv(config.get("GeneratedFiles", "country_borders"),
                        ("cluster_id", "border_list"),
                        keys,
                        [clusterDict[k] for k in keys])


class BorderGeoJSONWriter:
    '''
    Writes the country borders to a geojson file.
    '''

    def __init__(self, regionInfo, regionFile):
        '''
        Sets the class variables.
        '''
        self.regionFile = regionFile
        self.continents = self._buildContinentTrees(regionInfo)

    def _buildContinentTrees(self, regionInfo):
        '''
        Creates instances of the ContinentTree and Continent classes
        and uses them to create holes in the continents and returns
        the holey continents.
        '''

        trees = defaultdict(ContinentTree)
        for (regionId, clusterId, poly) in regionInfo:
            trees[clusterId].addContinent(Continent(poly))

        continents = {}
        for clusterId, tree in trees.items():
            tree.collapseHoles()
            continents[clusterId] = tree

        return continents

    def _generateJSONFeature(self, clusterId, continents):
        '''
        Creates the geojson geometries with the necessary properties.
        '''
        labels = Utils.read_features(self.regionFile)
        shapeList = []
        for child in continents:
            polygon = child.points
            shapeList.append(polygon)

        newMultiPolygon = MultiPolygon(shapeList)
        label = labels[clusterId].get("label", "Unknown")
        properties = {"clusterId": clusterId, "labels": label}
        return Feature(geometry=newMultiPolygon, properties=properties)

    def writeToFile(self, filename):
        '''
        Takes the geojson features and outpust a geojson file
        of the countries.
        '''
        featureList = []
        for clusterId, tree in self.continents.items():
            featureList.append(self._generateJSONFeature(clusterId, tree.root))
        collection = FeatureCollection(featureList)
        textDump = dumps(collection)
        with open(filename, "w") as writeFile:
            writeFile.write(textDump)


class ContinentTree:
    '''
    Holds a group of Continents.
    '''

    def __init__(self):
        self.root = set()

    def addContinent(self, newContinent):
        '''
        Sorts through the continents in the cluster group
        to find which ones are inside of eachother.
        '''
        for continent in self.root:
            path = mplPath.Path(continent.points[0])
            if path.contains_points(newContinent.points[0]).all():
                continent.addInnerContinent(newContinent)
                return
        self.root.add(newContinent)

    def collapseHoles(self):
        '''
        Calls the continents method to collapse holes.
        '''
        for continent in self.root:
            continent.collapseHoles()


class Continent:
    '''
    Is a polygon in Cluster, this class helps create
    holes/lakes in the cluster.
    '''

    def __init__(self, points):
        self.points = [points]
        self.children = set()

    def addInnerContinent(self, newContinent):
        '''
        Checks in the continents children are inside of eachother.
        '''
        for continent in self.children:
            path = mplPath.Path(continent.points[0])
            if path.contains_points(newContinent.points[0]).all():
                continent.addInnerContinent(newContinent)
                return
        self.children.add(newContinent)

    def collapseHoles(self):
        '''
        Collapses the holes inside of itself.
        '''
        for continent in list(self.children):
            continent.collapseHoles()
            for hole in continent.points:
                self.points.append(hole)
            self.children.remove(continent)
