import matplotlib.path as mplPath
from geojson import Feature, FeatureCollection
from geojson import dumps, MultiPolygon

from cartograph import Utils


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
        properties = {"clusterNum": index, "labels": label["label"][index]}
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
    '''
    '''

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
    '''
    '''

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
