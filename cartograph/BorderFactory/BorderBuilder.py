from _VoronoiWrapper import VoronoiWrapper
from _BorderProcessor import BorderProcessor
from cartograph import Util
from collections import defaultdict


class BorderBuilder:
    def __init__(self, config):
        self.x, self.y, self.clusterLabels = [], [], []
        self.minNumInCluster = config.getint("PreprocessingConstants", "min_num_in_cluster")
        self.blurRadius = config.getint("PreprocessingConstants", "blur_radius")
        self.minBorderNoiseLength = config.getfloat("PreprocessingConstants", "min_border_noise_length")
        self._initialize(config)

    def _initialize(self, config):
        featureDict = Util.read_features(config.get("PreprocessingFiles", "coordinates_with_water"),
                                         config.get("PreprocessingFiles", "clusters_with_water"),
                                         config.get("PreprocessingFiles", "denoised_with_id"))
        idList = list(featureDict.keys())
        for article in idList:
            if featureDict[article]["keep"] == "True":
                self.x.append(float(featureDict[article]["x"]))
                self.y.append(float(featureDict[article]["y"]))
                self.clusterLabels.append(int(featureDict[article]["cluster"]))

    def build(self):
        borders = defaultdict(list)
        vor = VoronoiWrapper(self.x, self.y, self.clusterLabels)
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
                while currentIndex != firstIndex:
                    # add to border
                    continent.append(edgeVertexDict[currentIndex])
                    # remove from available edge vertices
                    del edgeVertexDict[currentIndex]
                    # get list of two adjacent vertex indices
                    adjacent = edgeRidgeDict[currentIndex]
                    # pick the next vertex
                    nextIndex = adjacent[0] if adjacent[0] != prevIndex else adjacent[1]
                    prevIndex = currentIndex
                    currentIndex = edgeVertexDict[nextIndex].index
                del edgeVertexDict[firstIndex]
                # TODO: weight islands differently
                if len(continent) > self.minNumInCluster:
                    borders[label].append(continent)

        BorderProcessor(borders, self.blurRadius, self.minBorderNoiseLength).process()
        # remove water points
        del borders[len(borders) - 1]
        for label in borders:
            for continent in borders[label]:
                for i, vertex in enumerate(continent):
                    continent[i] = (vertex.x, vertex.y)
        return borders
