from math import pi, sqrt, acos
from geojson import Feature, FeatureCollection
from geojson import dumps, Polygon

# ===== Constants ===================
SEED_DISTANCE = .001


class Continent(object):

    def __init__(self, point):
        self.edges = []
        self.points = []
        self.center = point

    def __str__(self):
        retStr = ""
        for edge in self.edges:
            retStr += str(edge.getPoints()[1]) + "\n"
        return retStr

    def addEdge(self, pt1, pt2):
        xCenter, x1, x2 = self.center[0], pt1[0], pt2[0]
        yCenter, y1, y2 = self.center[1], pt1[1], pt2[1]
        a = sqrt((x1 - xCenter) ** 2 + (y1 - yCenter) ** 2)
        b = sqrt((x2 - xCenter) ** 2 + (y2 - yCenter) ** 2)
        c = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        theta = acos((a ** 2 + b ** 2 - c ** 2) / (2 * a * b))
        self.edges.append(Edgelet(pt1, pt2, theta))

    def addPoint(self, point):
        self.points.append(point)

    def numEdges(self):
        length = len(self.edges)
        return length

    def reduceToArray(self):
        self.edges.sort(key=lambda x: x.relTheta, reverse=False)
        if len(self.edges) != 0:
            ptArray = [edge.getPoints()[1] for edge in self.edges]
        else:
            ptArray = self.points
        return ptArray

    def generateJSONFeature(self):
        feature = self.reduceToArray()
        shape = Polygon([feature])
        return Feature(geometry=shape)


class Edgelet():
    def __init__(self, pt1, pt2, theta, height=SEED_DISTANCE):
        self.pt1 = pt1
        self.pt2 = pt2
        self.relativeHeight = height
        x1, x2 = pt1[1], pt2[1]
        y1, y2 = pt1[0], pt2[0]
        self.length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        self.relTheta = theta if theta < 2 * pi else theta - 2 * pi

    def generateChildren(self):
        '''
        Noisy edge generation mechanism
        TODO - Make Work
        '''
        pass

    def getPoints(self):
        return self.pt1, self.pt2


def continentListToFile(continentList, filename):
        continentList = [continent.generateJSONFeature()
                         for continent in continentList]
        collection = FeatureCollection(continentList)
        textDump = dumps(collection)
        with open(filename, "w") as writeFile:
            writeFile.write(textDump)
