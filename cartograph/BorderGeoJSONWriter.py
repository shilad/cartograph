from geojson import Feature, FeatureCollection
from geojson import dumps, Polygon
import matplotlib.path as mplPath
import Util
import Constants
import numpy as np

import Config
config = Config.BAD_GET_CONFIG()



class BorderGeoJSONWriter:

    def __init__(self, clusterList):
        biggestContinentIndexArray = self._buildBiggestContinentIndexArray(clusterList)
        self.continentTree = self._buildContinentTree(clusterList, biggestContinentIndexArray)

    @staticmethod
    def _buildBiggestContinentIndexArray(clusterList):
        biggestContinentIndexArray = []
        for cluster in clusterList:
            areaList = map(Util.calc_area, cluster)
            biggestContinentIndexArray.append(np.argmax(areaList))
        return biggestContinentIndexArray

    @staticmethod
    def _buildContinentTree(clusterList, biggestContinentIndexArray):
        continentTree = BorderGeoJSONWriter.ContinentTree()
        for clusterNum, cluster in enumerate(clusterList):
            for pos, continentPoints in enumerate(cluster):
                continent = BorderGeoJSONWriter.Continent(continentPoints, clusterNum, 0,
                                                          False, pos == biggestContinentIndexArray[clusterNum])
                continentTree.addContinent(continent)
        continentTree.collapseHoles()
        return continentTree

    @staticmethod
    def _generateJSONFeature(continent):
        label = Util.read_tsv(config.FILE_NAME_REGION_NAMES)
        shape = Polygon(continent.points)
        properties = {"clusterNum": continent.clusterNum}
        if continent.isBiggest:
            properties["labels"] = label["label"][continent.clusterNum]
        return Feature(geometry=shape, properties=properties)

    def writeToFile(self, filename):
        continentList = []
        searchStack = []
        for continent in self.continentTree.root:
            searchStack.append(continent)
        while searchStack:
            continent = searchStack.pop()
            for child in continent.children:
                searchStack.append(child)
            numToAdd = continent.depth + 1 - len(continentList)
            for _ in range(numToAdd):
                continentList.append([])
            continentList[continent.depth].append(continent)

        featureList = []
        for level in continentList:
            for continent in level:
                featureList.append(self._generateJSONFeature(continent))
        collection = FeatureCollection(featureList)
        textDump = dumps(collection)
        with open(filename, "w") as writeFile:
            writeFile.write(textDump)

    class Continent:

        def __init__(self, points, clusterNum, depth, isHole, isBiggest):
            self.points = [points]
            self.clusterNum = clusterNum
            self.children = set()
            self.depth = depth
            self.isHole = isHole
            self.isBiggest = isBiggest

        def addInnerContinent(self, newContinent):
            for continent in self.children:
                path = mplPath.Path(continent.points[0])
                if path.contains_points(newContinent.points[0]).all():
                    newContinent.depth = self.depth + 1
                    if self.clusterNum == newContinent.clusterNum:
                        newContinent.isHole = True
                    continent.addInnerContinent(newContinent)
                    return
            self.children.add(newContinent)

        def collapseHoles(self):
            for continent in list(self.children):
                if continent.isHole:
                    continent.collapseHoles()
                    for hole in continent.points:
                        self.points.append(hole)
                    self.children.remove(continent)

    class ContinentTree:
        def __init__(self):
            self.root = set()

        def addContinent(self, newContinent):
            for continent in self.root:
                path = mplPath.Path(continent.points[0])
                if path.contains_points(newContinent.points[0]).all():
                    newContinent.depth = continent.depth + 1
                    if continent.clusterNum == newContinent.clusterNum:
                        newContinent.isHole = True
                    continent.addInnerContinent(newContinent)
                    return
            self.root.add(newContinent)

        def collapseHoles(self):
            for continent in self.root:
                continent.collapseHoles()


