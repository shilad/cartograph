import logging
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
        points, lines, rings = self.createDictOfPoints(borders)
        BorderProcessor(borders, self.blurRadius, self.minBorderNoiseLength, waterLabel).process()
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
        tempDictOfPoints = {} # key = (x,y) value = pointId
        finalDictOfPoints = {} #key = pointId value = (x,y)

        tempDictOfLines = {} # key = (pointId, pointId) value = lineId
        finalDictOfLines = {} #key = lineId value = (pointId, pointId)

        finalDictOfRings = defaultdict(list) # key = ringId value = list of linesID that make that ring
        pointId = 0
        lineId = 0
        ringId = 0
        for key in borders.keys():
            listOfVertices = borders[key]
            for ring in listOfVertices:
                previousVertex = None
                pair = 0 #there is an edge between every 2 points (i.g between point 1 and 2, and then between 2 and 3.
                        # So will create a line between points only when pair is  odd
                for vertex in ring:
                    xy = (vertex.x, vertex.y)
                    if(xy not in tempDictOfPoints):
                        tempDictOfPoints[xy] = pointId
                        finalDictOfPoints[pointId] = xy
                        pointId += 1
                    if not previousVertex or pair % 2 == 0:
                        previousVertex = xy
                        pair += 1
                        continue
                    scrId = tempDictOfPoints[previousVertex]
                    destId = tempDictOfPoints[xy]
                    if((scrId, destId) not in tempDictOfLines):
                        tempDictOfLines[(scrId, destId)] = lineId
                        finalDictOfLines[lineId] = (scrId, destId)
                        lineId += 1
                    previousVertex = xy
                    pair += 1
                    currentLineId = tempDictOfLines[(scrId, destId)]
                    finalDictOfRings[ringId].append(currentLineId)
                ringId += 1
        print "points:", finalDictOfPoints
        print "lines:", finalDictOfLines
        print "rings:", finalDictOfRings
        return finalDictOfPoints, finalDictOfLines,finalDictOfRings



Config.initConf("./data/conf/summer2017_simple.txt")

bb = BorderBuilder(Config.get())
bb.build()