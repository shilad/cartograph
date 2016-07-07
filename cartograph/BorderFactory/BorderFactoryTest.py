import unittest
from _BorderProcessor import BorderProcessor


class BorderProcessorTest(unittest.TestCase):

    def test_makeNewRegionFromProcessed(self):
        processor = BorderProcessor({})
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


if __name__ == '__main__':
    unittest.main()