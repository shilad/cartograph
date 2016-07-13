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
    def perpendicular(v):
        p = np.empty_like(v)
        p[0] = -v[1]
        p[1] = v[0]
        return p

    @staticmethod
    def intersect(a0, a1, b0, b1):
        """Magical method of magic that returns intersection between lines defined by (pt0, pt1) and (pt2, pt3)
        http://www.cs.mun.ca/~rod/2500/notes/numpy-arrays/numpy-arrays.html"""
        d1 = a1 - a0
        d2 = b1 - b0
        d3 = a0 - b0
        perp = NoisyEdgesMaker.perpendicular(d1)
        denominator = np.dot(perp, d2)
        numerator = np.dot(perp, d3)
        return (numerator / denominator) * d2 + b0

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

    def _makeNoisyEdge(self, pt0, pt1, pt2, pt3, processed=False):
        u = np.subtract(pt2, pt0)
        v = np.subtract(pt1, pt0)
        if not processed:
            # check concavity
            w = np.subtract(pt1, pt2)
            bool0 = np.dot(u, v) > 0
            bool1 = np.dot(u, w) > 0
            convex = bool0 ^ bool1
            if not convex:
                midpoint = self.interpolate(pt0, pt2)
                perp = self.perpendicular(u)
                pointToUse = pt0 if bool0 and bool1 else pt2  # are the region points behind the second vertex?
                perpendicularPoint = np.add(midpoint, perp)
                newRegionPoint0 = self.intersect(pointToUse, pt1, midpoint, perpendicularPoint)
                newRegionPoint1 = self.intersect(pointToUse, pt3, midpoint, perpendicularPoint)
                self._makeNoisyEdge(pt0, newRegionPoint0, pt2, newRegionPoint1, True)
                return

        # check for large
        u = u / np.linalg.norm(u)
        dist = np.linalg.norm(v - u * np.dot(u, v))
        if dist > self.minBorderNoiseLength * 50:
            midpoint = self.interpolate(pt0, pt2)
            perp = self.perpendicular(u) * self.minBorderNoiseLength * 5
            pt1 = midpoint + perp
            pt3 = midpoint - perp
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
            points = [np.array(point) for point in vertex0.regionPoints & vertex1.regionPoints]
            assert len(points) == 2
            self._makeNoisyEdge(np.array((vertex0.x, vertex0.y)), points[0],
                                np.array((vertex1.x, vertex1.y)), points[1])
            for j in range(1, len(self.edge) - 1):
                noisedVertices.append(Vertex(None, self.edge[j], True))
            noisedVertices.append(vertex1)
        if circular:
            noisedVertices.pop()
        return noisedVertices
