import numpy as np
from Vertex import Vertex


class NoisyEdgesMaker:
    """
    Implementation based on https://github.com/amitp/mapgen2/blob/master/NoisyEdges.as
    """

    def __init__(self, vertices, minBorderNoiseLength):
        self.vertices = vertices
        self.minBorderNoiseLength = minBorderNoiseLength
        self.edge = []
        self.debug = []

    @staticmethod
    def interpolate(pt0, pt1, value=0.5):
        return pt1 + (np.subtract(pt0, pt1) * value)

    def _subdivide(self, a, b, c, d):
        if np.linalg.norm(np.subtract(b, a)) < self.minBorderNoiseLength or \
                np.linalg.norm(np.subtract(c, d)) < self.minBorderNoiseLength:
            return

        # get random center point
        rand0, rand1 = np.random.uniform(0.2, 0.8, 2)
        e = self.interpolate(a, d, rand0)
        f = self.interpolate(b, c, rand0)
        g = self.interpolate(a, b, rand1)
        i = self.interpolate(d, c, rand1)

        h = self.interpolate(e, f, rand1)  # center

        self.debug.extend([e, f, g, i])

        # make new quadrilaterals and recurse
        rand2, rand3 = np.random.uniform(0.6, 1.4, 2)
        self._subdivide(a, self.interpolate(g, b, rand2), h, self.interpolate(e, d, rand3))
        self.edge.append(h)
        self._subdivide(h, self.interpolate(f, c, rand2), c, self.interpolate(i, d, rand3))

    def _makeNoisyEdge(self, pt0, pt1, pt2, pt3):
        midpoint = self.interpolate(pt0, pt2)
        mid0 = self.interpolate(pt0, pt1)
        mid1 = self.interpolate(pt1, pt2)
        mid2 = self.interpolate(pt2, pt3)
        mid3 = self.interpolate(pt3, pt0)
        self._subdivide(pt0, mid0, midpoint, mid3)
        self.edge.append(midpoint)
        self._subdivide(midpoint, mid1, pt2, mid2)

    def makeNoisyEdges(self, circular):
        if circular:
            self.vertices.append(self.vertices[0])
        noisedVertices = [self.vertices[0]]
        for i in range(len(self.vertices) - 1):
            self.edge = []
            vertex0 = self.vertices[i]
            vertex1 = self.vertices[i + 1]
            points = list(vertex0.regionPoints & vertex1.regionPoints)
            assert len(points) == 2
            self._makeNoisyEdge((vertex0.x, vertex0.y), points[0], (vertex1.x, vertex1.y), points[1])
            for j in range(1, len(self.edge) - 1):
                noisedVertices.append(Vertex(None, self.edge[j], True))
            noisedVertices.append(vertex1)
        if circular:
            noisedVertices.pop()
        return noisedVertices
