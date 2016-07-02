from _VoronoiWrapper import VoronoiWrapper
from _BorderProcessor import BorderProcessor
from cartograph import Util, Config
from collections import defaultdict

config = Config.BAD_GET_CONFIG()


class BorderBuilder:
    def __init__(self, x, y, clusterLabels):
        self.x = x
        self.y = y
        self.clusterLabels = clusterLabels

    @classmethod
    def from_file(cls, ):
        s = "../../" if debug else ""
        featureDict = Util.read_features(s + config.FILE_NAME_WATER_AND_ARTICLES,
                                         s + config.FILE_NAME_KEEP,
                                         s + config.FILE_NAME_WATER_CLUSTERS)
        idList = list(featureDict.keys())
        x, y, clusters = [], [], []
        for article in idList:
            if featureDict[article]["keep"] == "True":
                x.append(float(featureDict[article]["x"]))
                y.append(float(featureDict[article]["y"]))
                clusters.append(int(featureDict[article]["cluster"]))
        return cls(x, y, clusters)

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
                if len(continent) > config.MIN_NUM_IN_CONTINENT:
                    borders[label].append(continent)

        BorderProcessor(borders).process()
        # remove water points
        del borders[len(borders) - 1]
        for label in borders:
            for continent in borders[label]:
                for i, vertex in enumerate(continent):
                    continent[i] = (vertex.x, vertex.y)
        return borders

debug = False

if __name__ == '__main__':
    debug = True
    BorderBuilder.from_file().build()
