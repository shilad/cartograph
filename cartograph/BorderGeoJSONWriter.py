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


class BorderGeoJSONWriter:

    def __init__(self, clusterList, regionFile):
        self.regionFile = regionFile
        self.clusterList = self._buildContinentTree(clusterList)

    def _buildContinentTree(self, clusterList):
        continents = []
        for cluster in clusterList:
            continentTree = ContinentTree()
            for polygon in cluster:
                shape = Continent(polygon)
                continentTree.addContinent(shape)
            continentTree.collapseHoles()
            continents.append(continentTree)
        return continents

    def _generateJSONFeature(self, index, continents):
        label = Utils.read_tsv(self.regionFile)
        shapeList = []
        for child in continents:
            polygon = child.points
            shapeList.append(polygon)

        newMultiPolygon = MultiPolygon(shapeList)
        try:
            properties = {"clusterNum": index, "labels": label["label"][index]}
        except IndexError:
            properties = {"clusterNum": index, "labels": "Cluster %s" % (index)}
        return Feature(geometry=newMultiPolygon, properties=properties)

    def writeToFile(self, filename):
        featureList = []
        for index, tree in enumerate(self.clusterList):
            featureList.append(self._generateJSONFeature(index, tree.root))
        collection = FeatureCollection(featureList)
        textDump = dumps(collection)
        with open(filename, "w") as writeFile:
            writeFile.write(textDump)


class ContinentTree:
    def __init__(self):
        self.root = set()

    def addContinent(self, newContinent):
        for continent in self.root:
            path = mplPath.Path(continent.points[0])
            if path.contains_points(newContinent.points[0]).all():
                continent.addInnerContinent(newContinent)
                return
        self.root.add(newContinent)

    def collapseHoles(self):
        for continent in self.root:
            continent.collapseHoles()


class Continent:

    def __init__(self, points):
        self.points = [points]
        self.children = set()

    def addInnerContinent(self, newContinent):
        for continent in self.children:
            path = mplPath.Path(continent.points[0])
            if path.contains_points(newContinent.points[0]).all():
                continent.addInnerContinent(newContinent)
                return
        self.children.add(newContinent)

    def collapseHoles(self):
        for continent in list(self.children):
            continent.collapseHoles()
            for hole in continent.points:
                self.points.append(hole)
            self.children.remove(continent)
