import unittest
from BorderProcessor import BorderProcessor
from Noiser import NoisyEdgesMaker
from Vertex import Vertex
from matplotlib import pyplot as plt
import math


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
        # plt.scatter(zip(*debug)[0], zip(*debug)[1], c="y")
        plt.show()

if __name__ == '__main__':
    unittest.main()