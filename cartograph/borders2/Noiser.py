import numpy as np
from Vertex import Vertex


class NoisyEdgesMaker:
    """
    Implementation based on https://github.com/amitp/mapgen2/blob/master/NoisyEdges.as,
    but improved to account for concave quadrilaterals formed by the Voronoi vertices and the
    region points.
    """

    def __init__(self, vertices, minBorderNoiseLength):
        self.vertices = vertices
        self.minBorderNoiseLength = minBorderNoiseLength
        self.edge = []


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
        """
        Subdivide the quadrilateral into smaller segments, adding the center to the edge
        """
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

        # make new quadrilaterals and recurse
        rand2, rand3 = np.random.uniform(0.6, 1.4, 2)
        self._subdivide(a, self.interpolate(g, b, rand2), h, self.interpolate(e, d, rand3))
        self.edge.append(h)
        self._subdivide(h, self.interpolate(f, c, rand2), c, self.interpolate(i, d, rand3))


    def _makeNoisyEdge(self, pt0, pt1, pt2, pt3, processed=False):
        """
        Make a noisy edge from two Voronoi vertices (pt0 and pt2) and two region points (pt1 and pt3)
        """
        u = np.subtract(pt2, pt0)
        v = np.subtract(pt1, pt0)

        # check concavity
        if not processed:
            w = np.subtract(pt1, pt2)
            bool0 = np.dot(u, v) > 0
            bool1 = np.dot(u, w) > 0
            convex = bool0 ^ bool1
            if not convex:
                midpoint = self.interpolate(pt0, pt2)
                perp = self.perpendicular(u)
                pointToUse = pt0 if bool0 and bool1 else pt2  # are the region points behind the second vertex?
                perpendicularPoint = np.add(midpoint, perp)
                pt1 = self.intersect(pointToUse, pt1, midpoint, perpendicularPoint)
                pt3 = self.intersect(pointToUse, pt3, midpoint, perpendicularPoint)
                self._makeNoisyEdge(pt0, pt1, pt2, pt3, True)
                return

        # check for large or small
        dist = np.linalg.norm(u)
        u = u / dist  # numpy doesn't like augmented assignment here
        distToRegionPoint = np.linalg.norm(v - u * np.dot(u, v))
        multiplier = np.clip(distToRegionPoint,
                             min(self.minBorderNoiseLength / 10, dist * 1.61803398875),  # golden ratio, cause why not?
                             self.minBorderNoiseLength * 10)

        midpoint = self.interpolate(pt0, pt2)
        perp = self.perpendicular(u) * multiplier
        pt1 = midpoint + perp
        pt3 = midpoint - perp

        mid0 = self.interpolate(pt0, pt1)
        mid1 = self.interpolate(pt1, pt2)
        mid2 = self.interpolate(pt2, pt3)
        mid3 = self.interpolate(pt3, pt0)
        self._subdivide(pt0, mid0, midpoint, mid3)
        self.edge.append(midpoint)
        self._subdivide(midpoint, mid1, pt2, mid2)

    def makeNoisyEdges(self, circular):
        """
        Make a noisy edge from the list of vertices given in the constructor
        Args:
            circular: Whether or not the region is circular

        Returns:
            A new list of Vertex objects defining the new noised border. The new vertices will have index None, but
            the original information from the input vertices is preserved (i.e., new vertices are added in between
            the input ones).
        """
        if circular:
            self.vertices.append(self.vertices[0])
        noisedVertices = [self.vertices[0]]
        for i in range(len(self.vertices) - 1):
            self.edge = []
            vertex0 = self.vertices[i]
            vertex1 = self.vertices[i + 1]

            if(vertex0.regionPoints is  None and vertex1.regionPoints is  None ):print False
           # if (vertex1.regionPoints is not None): print False

            points = [np.array(point) for point in vertex0.regionPoints & vertex1.regionPoints]
          #  if (vertex0.regionPoints is not None and vertex1.regionPoints is not None): print points
            assert len(points) == 2


            self._makeNoisyEdge(np.array((vertex0.x, vertex0.y)), points[0],
                                np.array((vertex1.x, vertex1.y)), points[1])

            for j in range(1, len(self.edge) - 1):

                noisedVertices.append(Vertex(None, self.edge[j], True))
            noisedVertices.append(vertex1)
        if circular:
            noisedVertices.pop()
        return noisedVertices

    def makeNoisyEdges_new(self, commonLines, pointsDict, circular, idGenerator, linesDict, processedLines):
        '''
        case 1: both lines i and i+1 have been processed
        case 2: just line 1 has been processed
        case 3: just line i+1 has been processed
        case 4: none of the lines have been processed
        :param commonLines:
        :param pointsDict:
        :param circular:
        :param idGenerator:
        :param linesDict:
        :param processedLines:
        :return:
        '''
        noised = []
        print 'here'
        for i in range(len(commonLines)-1):
            if commonLines[i] in processedLines:
                processedLines1 = processedLines[commonLines[i]]
            if commonLines[i+1] in processedLines:
                processedLines2 = processedLines[commonLines[i+1]]

            commonPoints = linesDict[commonLines[i]] + linesDict[commonLines[i + 1]]

            print commonPoints
            noisedPoints = [commonPoints[0]]
            for k in range(len(commonPoints)-1):
                self.edge = []


                vertex0 = pointsDict[commonPoints[k]]
                vertex1 = pointsDict[commonPoints[k+1]]
                #print len(vertex0)
                #print 'vertex', vertex0[-1]
                assert len(set(vertex0[-1])) == 3
                assert len(set(vertex1[-1])) == 3

                points  = [np.array(point) for point in set(vertex0[-1]) & set(vertex1[-1])]
                #if len(points) != 2: print points
                assert len(points) == 2
                    #why not always 2 len == 2???
               # print points
                self._makeNoisyEdge(np.array((vertex0[0], vertex0[1])), points[0],
                                    np.array((vertex1[0], vertex1[1])), points[1])


                id = idGenerator.getNextID()

                for j in range(1, len(self.edge) - 1):
                    pointsDict['n' + str(id)] = self.edge[j][0], self.edge[j][1]
                    noisedPoints.append('n' + str(id))
                    id = idGenerator.getNextID()
                    noisedPoints.append(commonPoints[k+1])

                    if circular:
                        noisedPoints.pop()
                    noised.extend(noisedPoints)
        return noised, pointsDict

        def makeLineDictOutOFNewPointDict(self, newPointIdList, idGenerator):
            previous = None
            pair = 0
            lineId = idGenerator.getNextID()
            newLinesID = []
            for newPointId in newPointIdList:
                if previous != None and pair % 2 != 0:
                    self.lines['n' + str(lineId)] = (previous, newPointId)
                    newLinesID.append('n' + str(lineId))
                    lineId = idGenerator.getNextID()
                previous = newPointId
                pair += 1
            return newLinesID