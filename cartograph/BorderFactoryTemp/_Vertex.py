# wrapper object for vertices
class Vertex:

    def __init__(self, index, point, isCoast):
        self.index = index
        self.x = point[0]
        self.y = point[1]
        self.isCoast = isCoast
        self.point_indices = set()

    def addPointIndices(self, indices):
        self.point_indices.update(indices)