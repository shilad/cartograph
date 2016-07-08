# wrapper object for vertices
# TODO: add more information so that edgeRidgeDict and edgeVertexDict can be constructed from Vertex objects


class Vertex:

    def __init__(self, index, point, isOnCoast):
        self.index = index
        self.x = point[0]
        self.y = point[1]
        self.isOnCoast = isOnCoast
        self.regionPoints = set()

    def addRegionPoints(self, points):
        self.regionPoints.update(points)