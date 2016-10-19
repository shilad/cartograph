import logging
from collections import defaultdict

from BorderProcessor import BorderProcessor
from VoronoiWrapper import VoronoiWrapper
from cartograph import Utils

logger = logging.getLogger('luigi-interface')


class BorderBuilder:
    def __init__(self, config):
        self.x, self.y, self.clusterLabels = [], [], []
        self.minNumInCluster = config.getint("PreprocessingConstants", "min_num_in_cluster")
        self.blurRadius = config.getint("PreprocessingConstants", "blur_radius")
        self.minBorderNoiseLength = config.getfloat("PreprocessingConstants", "min_border_noise_length")
        self._initialize(config)

    def _initialize(self, config):
        featureDict = Utils.read_features(config.getSample("GeneratedFiles", "coordinates_with_water"),
                                          config.getSample("GeneratedFiles", "clusters_with_water"),
                                          config.getSample("GeneratedFiles", "denoised_with_id"))
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
        BorderProcessor(borders, self.blurRadius, self.minBorderNoiseLength, waterLabel).process()
        # remove water points
        del borders[waterLabel]
        for label in borders:
            for continent in borders[label]:
                for i, vertex in enumerate(continent):
                    continent[i] = (vertex.x, vertex.y)
        return borders
