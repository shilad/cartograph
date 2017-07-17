import logging
import numpy as np
from collections import defaultdict

from BorderProcessor import BorderProcessor
from VoronoiWrapper import VoronoiWrapper
from cartograph import Utils

logger = logging.getLogger('luigi-interface')
from cartograph import Config

class BorderBuilder:
    def __init__(self, config):
        self.x, self.y, self.clusterLabels = [], [], []
        self.minNumInCluster = config.getint("PreprocessingConstants", "min_num_in_cluster")
        self.blurRadius = config.getint("PreprocessingConstants", "blur_radius")
        self.minBorderNoiseLength = config.getfloat("PreprocessingConstants", "min_border_noise_length")

        self._initialize(config)

    def _initialize(self, config):

        if config.sampleBorders():

            featureDict = Utils.read_features(config.getSample("GeneratedFiles", "coordinates_with_water"),
                                              config.getSample("GeneratedFiles", "clusters_with_water"),
                                              config.getSample("GeneratedFiles", "denoised_with_id"))
        else:
            featureDict = Utils.read_features(config.get("GeneratedFiles", "coordinates_with_water"),
                                              config.get("GeneratedFiles", "clusters_with_water"),
                                              config.get("GeneratedFiles", "denoised_with_id"))
        idList = list(featureDict.keys())
        for article in idList:
            if featureDict[article]["keep"] == "True":
                self.x.append(float(featureDict[article]["x"]))
                self.y.append(float(featureDict[article]["y"]))
                self.clusterLabels.append(int(featureDict[article]["cluster"]))

    def build(self):

        borders = defaultdict(list)
        waterLabel = max(self.clusterLabels)
        logger.info("Starting Voronoi tessellation.")
        vor = VoronoiWrapper(self.x, self.y, self.clusterLabels, waterLabel)
        logger.info("Building borders.")
        for label in vor.edgeRidgeDict:
            edgeRidgeDict = vor.edgeRidgeDict[label]
            edgeVertexDict = vor.edgeVertexDict[label]
            while edgeVertexDict:
                continent = []
                # pick arbitrary element from dictionary
                firstIndex = edgeVertexDict.keys()[0]
                firstVertex = edgeVertexDict[firstIndex]
                prevIndex = firstIndex
                continent.append(firstVertex)
                # there are two options, just pick the first one
                currentIndex = edgeRidgeDict[firstIndex][0]
                isIsland = firstVertex.isOnCoast
                while currentIndex != firstIndex:
                    vertex = edgeVertexDict[currentIndex]
                    isIsland = isIsland and vertex.isOnCoast
                    # add to border
                    continent.append(vertex)
                    # remove from available edge vertices
                    del edgeVertexDict[currentIndex]
                    # get list of two adjacent vertex indices
                    adjacent = edgeRidgeDict[currentIndex]
                    # pick the next vertex
                    nextIndex = adjacent[0] if adjacent[0] != prevIndex else adjacent[1]
                    prevIndex = currentIndex
                    currentIndex = edgeVertexDict[nextIndex].index
                del edgeVertexDict[firstIndex]
                minNumNecessary = self.minNumInCluster / 50 if isIsland else self.minNumInCluster
                if len(continent) > minNumNecessary:
                    borders[label].append(continent)
                else:
                    borders[waterLabel].append(continent)

        logger.info("Processing borders.")
        #make a set of all points
        #create a dictionary where the id is point id, value is x,y (ids are created through enumerating)
        #maybe play around with collapsing/creating holes
        #print(borders)
        temppoints, finalpoints = self.createDictOfPoints(borders)
        templines, finallines = self.createDictOfLines(borders, temppoints)
        temprings, finalrings = self.createDictOfRings(borders, temppoints, templines)
        tempregions, finalregions = self.createDictOfRegions(borders, temppoints, templines, temprings)
        BorderProcessor(borders, self.blurRadius, self.minBorderNoiseLength, waterLabel, finalpoints, finallines,
                        finalrings, finalregions).process()
        # remove water points
        del borders[waterLabel]
        # make a big point list
        # make edges be ids of points
        # make "continents" aka regions be edge indices
        for label in borders:
            for continent in borders[label]:
                for i, vertex in enumerate(continent):
                    continent[i] = (vertex.x, vertex.y)

        return borders

    def createDictOfPoints(self, borders):
        tempDictOfPoints = {}  # key = (x,y, isOnCoast, regionPoints) value = pointId
        finalDictOfPoints = {}  # key = pointId value = (x,y, isOnCoast, regionPoints)
        pointId = 0
        for clusterLabels in borders.keys():
            for regions in borders[clusterLabels]:
                for vertex in regions:
                    info = (vertex.x, vertex.y, vertex.isOnCoast, tuple(sorted(vertex.regionPoints)))
                    if (info not in tempDictOfPoints.keys()):
                        tempDictOfPoints[info] = pointId
                        finalDictOfPoints[pointId] = info
                        pointId += 1
        return tempDictOfPoints, finalDictOfPoints

    def createDictOfLines(self, borders, tempDictOfPoints):
        tempDictOfLines = {}  # key = (pointId, pointId) value = lineId
        finalDictOfLines = {}  # key = lineId value = (pointId, pointId)
        lineId = 0
        for clusterLabels in borders.keys():
            for regions in borders[clusterLabels]:
                previousVertex = None
                for x in range(len(regions) + 1):
                    if previousVertex is not None:
                        pointidPair = (tempDictOfPoints[(previousVertex.x, previousVertex.y, previousVertex.isOnCoast,
                                                         tuple(sorted(previousVertex.regionPoints)))],
                                       tempDictOfPoints[(regions[x % len(regions)].x, regions[x % len(regions)].y,
                                                         regions[x % len(regions)].isOnCoast,
                                                         tuple(sorted(regions[x % len(regions)].regionPoints)))])
                        tempDictOfLines[pointidPair] = lineId
                        finalDictOfLines[lineId] = pointidPair
                        lineId += 1
                    previousVertex = regions[x % len(regions)]
        return tempDictOfLines, finalDictOfLines

    def createDictOfRings(self, borders, tempDictOfPoints, tempDictOfLines):
        tempDictOfRings = {} # key = (lineId, lineId... lineId) value =  ringId
        finalDictOfRings = defaultdict(tuple)  # key = ringId value = (lineId, lineId... lineId)
        ringId = 0
        for clusterLabels in borders.keys():
            for regions in borders[clusterLabels]:
                previousVertex = None
                for x in range(len(regions) + 1):
                    if previousVertex is not None:
                        pointidPair = (tempDictOfPoints[(previousVertex.x, previousVertex.y, previousVertex.isOnCoast,
                                                         tuple(sorted(previousVertex.regionPoints)))],
                                       tempDictOfPoints[(regions[x % len(regions)].x, regions[x % len(regions)].y,
                                                         regions[x % len(regions)].isOnCoast,
                                                         tuple(sorted(regions[x % len(regions)].regionPoints)))])
                        lineId = tempDictOfLines[pointidPair]
                        finalDictOfRings[ringId] += (lineId,)
                    if x == len(regions):
                        lineIds = finalDictOfRings[ringId]
                        tempDictOfRings[lineIds] = ringId
                    previousVertex = regions[x % len(regions)]
                ringId += 1
        return tempDictOfRings, finalDictOfRings

    def createDictOfRegions(self, borders, tempDictOfPoints, tempDictOfLines, tempDictOfRings):
        tempDictOfRegions = {} #key = (ringId, ringId... ringId), value = clusterId
        finalDictOfRegions = defaultdict(tuple)  # key = clusterId value = (ringId, ringId... ringId)
        for clusterLabels in borders.keys():
            for regions in borders[clusterLabels]:
                lineIds = tuple()
                previousVertex = None
                for x in range(len(regions) + 1):
                    if previousVertex is not None:
                        pointidPair = (tempDictOfPoints[(previousVertex.x, previousVertex.y, previousVertex.isOnCoast,
                                                         tuple(sorted(previousVertex.regionPoints)))],
                                       tempDictOfPoints[(regions[x % len(regions)].x, regions[x % len(regions)].y,
                                                         regions[x % len(regions)].isOnCoast,
                                                         tuple(sorted(regions[x % len(regions)].regionPoints)))])
                        lineId = tempDictOfLines[pointidPair]
                        lineIds += (lineId,)
                    if x == len(regions):
                        finalDictOfRegions[clusterLabels] += (tempDictOfRings[lineIds],)
                        tempDictOfRegions[(tempDictOfRings[lineIds],)] = clusterLabels
                    previousVertex = regions[x % len(regions)]
        return tempDictOfRegions, finalDictOfRegions

Config.initConf("./data/conf/summer2017_simple.txt")

bb = BorderBuilder(Config.get())
bb.build()