import unittest
from BorderProcessor import BorderProcessor
from BorderBuilder import BorderBuilder
from Noiser import NoisyEdgesMaker
from Vertex import Vertex
from matplotlib import pyplot as plt
import matplotlib.path as mplPath
import math
import random
import numpy as np
from scipy.spatial import Voronoi, voronoi_plot_2d


class BorderProcessorTest(unittest.TestCase):

    def test_makeNewRegionFromProcessed(self):
        processor = BorderProcessor({}, 5, 0.1, 13)
        region = [(1, 1), (2, 2), (3, 3), (4, 5), (5, 5)]
        processed = [[(1, 2), (3, 4)]]
        stopStartList = [(1, 2)]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList)
        self.assertEqual([tuple(point) for point in processedRegion], [(1, 1), (1, 2), (3, 4), (4, 5), (5, 5)])

        stopStartList = [(4, 0)]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList)
        self.assertEqual([tuple(point) for point in processedRegion], [(2, 2), (3, 3), (4, 5), (1, 2), (3, 4)])

        stopStartList = [(0, 4)]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList, reverse=True)
        self.assertEqual([tuple(point) for point in processedRegion], [(2, 2), (3, 3), (4, 5), (3, 4), (1, 2)])

        region = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9)]
        processed = [[(1, 2), (3, 4), (5, 6)], [(-1, 2), (-2, 3), (-3, 4), (-5, 6)]]
        stopStartList = [(1, 1), (9, 9)]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList)
        self.assertEquals([tuple(point) for point in processedRegion],
                          [(0, 0),
                           (1, 2), (3, 4), (5, 6),
                           (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8),
                           (-1, 2), (-2, 3), (-3, 4), (-5, 6)])

        stopStartList = [(9, 2), (3, 3)]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList)
        self.assertEquals([tuple(point) for point in processedRegion],
                          [(-1, 2), (-2, 3), (-3, 4), (-5, 6),
                           (4, 4), (5, 5), (6, 6), (7, 7), (8, 8),
                           (1, 2), (3, 4), (5, 6)])

        processed = [[(1, 2), (2, 3), (3, 4), (5, 6)], [(-1, 2)], [(-3, 2)], [(-7, 5), (5, 6)]]
        stopStartList = [(0, 4), (6, 6), (7, 7), (8, 9)]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList)
        self.assertEquals([tuple(point) for point in processedRegion],
                          [(1, 2), (2, 3), (3, 4), (5, 6),
                           (5, 5),
                           (-1, 2),
                           (-3, 2),
                           (-7, 5), (5, 6)])

        processed = [[(-3, 2)], [(-7, 5), (5, 6)], [(1, 2), (2, 3), (3, 4), (5, 6)], [(-1, 2)]]
        stopStartList = [(4, 4), (2, 1), (0, 8), (6, 6)]
        # [[6, 6], [8, 0], [1, 2], [4, 4]]
        processedRegion = processor.makeNewRegionFromProcessed(region, processed, stopStartList, reverse=True)
        self.assertEquals([tuple(point) for point in processedRegion],
                          [(5, 6), (-7, 5),
                           (3, 3),
                           (-3, 2),
                           (5, 5),
                           (-1, 2),
                           (7, 7),
                           (5, 6), (3, 4), (2, 3), (1, 2)])

    def test_Noiser(self):
        points = [(0, 0), (1, 0), (0.5, math.sqrt(3)/2)]  # , (10, 5), (10,10)]
        vertices = [Vertex(None, point, True) for point in points]
        center = (0.5, 1/(2*math.sqrt(3)))
        circular = True
        regionPoints = [(center[0], -center[1]), center, (1, 1/math.sqrt(3)), center, (0.1, 0.3), center]
        for i in range(len(vertices) - 1):
            regionPts = [regionPoints[2*i], regionPoints[2*i + 1]]
            vertices[i].addRegionPoints(regionPts)
            vertices[i+1].addRegionPoints(regionPts)
        if circular:
            vertices[-1].addRegionPoints([regionPoints[-1], regionPoints[-2]])
            vertices[0].addRegionPoints([regionPoints[-1], regionPoints[-2]])
        maker = NoisyEdgesMaker(vertices, 0.001)
        noisedVertices = maker.makeNoisyEdges(circular)
        x = [v.x for v in noisedVertices]
        y = [v.y for v in noisedVertices]
        plt.plot(x, y)
        xPoints = zip(*points)[0]
        yPoints = zip(*points)[1]
        plt.scatter(xPoints, yPoints, c="r")
        xRegion = zip(*regionPoints)[0]
        yRegion = zip(*regionPoints)[1]
        plt.scatter(xRegion, yRegion, c="g")
        # debug = maker.debug
        # plt.scatter(zip(*debug)[0], zip(*debug)[1], c="y", s=0.1)
        # plt.show()

    @staticmethod
    def generatePolygon(ctrX, ctrY, aveRadius, irregularity, spikeyness, numVerts):
        '''Start with the centre of the polygon at ctrX, ctrY,
            then creates the polygon by sampling points on a circle around the centre.
            Randon noise is added by varying the angular spacing between sequential points,
            and by varying the radial distance of each point from the centre.

            Params:
            ctrX, ctrY - coordinates of the "centre" of the polygon
            aveRadius - in px, the average radius of this polygon, this roughly controls how large the polygon is, really only useful for order of magnitude.
            irregularity - [0,1] indicating how much variance there is in the angular spacing of vertices. [0,1] will map to [0, 2pi/numberOfVerts]
            spikeyness - [0,1] indicating how much variance there is in each vertex from the circle of radius aveRadius. [0,1] will map to [0, aveRadius]
            numVerts - self-explanatory

            Returns a list of vertices, in CCW order.
            '''

        irregularity = np.clip(irregularity, 0, 1) * 2 * math.pi / numVerts
        spikeyness = np.clip(spikeyness, 0, 1) * aveRadius

        # generate n angle steps
        angleSteps = []
        lower = (2 * math.pi / numVerts) - irregularity
        upper = (2 * math.pi / numVerts) + irregularity
        sum = 0
        for i in range(numVerts):
            tmp = random.uniform(lower, upper)
            angleSteps.append(tmp)
            sum = sum + tmp

        # normalize the steps so that point 0 and point n+1 are the same
        k = sum / (2 * math.pi)
        for i in range(numVerts):
            angleSteps[i] = angleSteps[i] / k

        # now generate the points
        points = []
        angle = random.uniform(0.1, 2 * math.pi)
        for i in range(numVerts):
            r_i = np.clip(random.gauss(aveRadius, spikeyness), aveRadius/2, 2 * aveRadius)
            x = ctrX + r_i * math.cos(angle)
            y = ctrY + r_i * math.sin(angle)
            points.append((int(x), int(y)))

            angle = angle + angleSteps[i]

        return points

    class TestBorderBuilder(BorderBuilder):
        def __init__(self, x, y, clusterLabels, minNumInCluster=5, blurRadius=5, minBorderNoiseLength=0.01):
            self.x = x
            self.y = y
            self.clusterLabels = clusterLabels
            self.minNumInCluster = minNumInCluster
            self.blurRadius = blurRadius
            self.minBorderNoiseLength = minBorderNoiseLength

    @staticmethod
    def _addRandomPoints(x, y, waterLevel):
        length = len(x)
        np.random.seed(42)
        randX = np.random.uniform(np.min(x) - 3,
                                    np.max(x) + 3,
                                    int(length * waterLevel))
        randY = np.random.uniform(np.min(x) - 3,
                                    np.max(x) + 3,
                                    int(length * waterLevel))
        x = np.append(x, randX)
        y = np.append(y, randY)
        return x, y

    def test_BorderBuilder(self):
        plt.clf()
        polygon = self.generatePolygon(0, 0, 5, 0.1, 0.1, 50)
        polygon.append(polygon[0])
        x, y = zip(*polygon)
        # plt.plot(x, y)
        x, y = self._addRandomPoints(x, y, 10)
        points = zip(x, y)

        vor = Voronoi(points)
        voronoi_plot_2d(vor)
        # plt.show()

        labels = map(int, mplPath.Path(polygon).contains_points(points))
        waterX, waterY, insideX, insideY = [], [], [], []
        for i in range(len(x)):
            if labels[i]:
                insideX.append(x[i])
                insideY.append(y[i])
            else:
                waterX.append(x[i])
                waterY.append(y[i])
        # plt.scatter(insideX, insideY, c="g")
        # plt.scatter(waterX, waterY, c="b")
        # plt.show()
        borders = self.TestBorderBuilder(x, y, labels).build()
        region = borders[0]
        for section in region:
            section.append(section[0])
            x, y = zip(*section)
            plt.plot(x, y)
        plt.show()


if __name__ == '__main__':
    unittest.main()