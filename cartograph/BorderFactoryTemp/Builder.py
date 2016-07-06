from _VoronoiWrapper import VoronoiWrapper
from _BorderProcessor import BorderProcessor
from cartograph import Util
from collections import defaultdict


class Builder:
    def __init__(self, x, y, clusterLabels, minNumInCluster):
        self.x = x
        self.y = y
        self.clusterLabels = clusterLabels
        self.minNumInCluster = minNumInCluster

    @classmethod
    def from_file(cls, featureDict, minNumInCluster):
        idList = list(featureDict.keys())
        x, y, clusters = [], [], []
        for article in idList:
            if featureDict[article]["keep"] == "True":
                x.append(float(featureDict[article]["x"]))
                y.append(float(featureDict[article]["y"]))
                clusters.append(int(featureDict[article]["cluster"]))
        return cls(x, y, clusters, minNumInCluster)

    def build(self, blurRadius):
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
                if len(continent) > self.minNumInCluster:
                    borders[label].append(continent)

        # temp debug code
        for label in borders:
            for continent in borders[label]:
                for i, vertex in enumerate(continent):
                    continent[i] = tuple(vertex.point)

        BorderProcessor(borders, blurRadius).process()
        del borders[len(borders)-1]
        return borders
