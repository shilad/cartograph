import numpy as np
from cartograph import Config
config = Config.BAD_GET_CONFIG()


class BorderProcessor:
    def __init__(self, borders):
        self.borders = borders

    @staticmethod
    def _wrapRange(start, stop, length, reverse=False):
        """
        Returns:
            range from start to stop *inclusively* modulo length
        """
        start %= length
        stop %= length
        if reverse:
            if stop > start:
                return range(start, -1, -1) + range(length - 1, stop - 1, -1)
            else:
                return range(start, stop - 1, -1)
        else:
            if start > stop:
                return range(start, length) + range(0, stop + 1)
            else:
                return range(start, stop + 1)

    @staticmethod
    def _blur(array, circular, radius):
        # arrays which are shorter than this will be blurred to a single point
        if len(array) <= radius * 2 + 1:
            return array
        blurred = []
        if circular:
            for i, _ in enumerate(array):
                start = i - radius
                stop = i + radius
                neighborhood = [
                    array[j] for j in BorderProcessor._wrapRange(start, stop, len(array))]
                blurred.append(np.average(neighborhood))
        else:
            for i, _ in enumerate(array):
                start = max(0, i - radius)
                stop = min(len(array) - 1, i + radius)
                neighborhood = [array[j] for j in range(start, stop + 1)]
                blurred.append(np.average(neighborhood))
        return blurred

    @staticmethod
    def _processVertices(vertices, circular):
        """
        Processes the list of vertices based on whether they are part of a coast or not
        Args:
            vertices: list of Vertex objects
            circular: whether or not the list forms a circular border

        Returns:
            A list of modified vertices (can be longer than input)
        """
        if len(vertices) < 2:
            return vertices
        # if vertices[0].is_edge_coast(vertices[1], BorderFactory.water_label):
        #     x, y = [], []
        #     for i in range(len(vertices) - 1):
        #         x, y = _NoisyEdgesMaker()
        # else:
        x = [vertex.x for vertex in vertices]
        y = [vertex.y for vertex in vertices]
        x = BorderProcessor._blur(x, circular, config.BLUR_RADIUS)
        y = BorderProcessor._blur(y, circular, config.BLUR_RADIUS)
        for i, vertex in enumerate(vertices):
            vertex.x = x[i]
            vertex.y = y[i]
        return vertices

    @staticmethod
    def _getConsensusBorderIntersection(indices1, indices2, len1, len2, reverse2):
        """
        Args:
            indices1: *aligned* indices of points in points1 which are in intersection
            indices2: *aligned* indices of points in points2 which are in intersection
            len1: length of points1
            len2: length of points2
            reverse2: Whether or not indices2 is in reversed order
        Returns:
            list of lists of contiguous regions, whether the border is circle, and reverse2 (for convenience)
        """
        if len(indices1) != len(indices2):
            raise ValueError("Lists of indices must be the same length.")

        # build list for each contiguous region
        diff2 = -1 if reverse2 else 1
        consensusLists = [[(indices1[0], indices2[0])]]
        for i in range(1, len(indices1)):
            prev = consensusLists[-1][-1]
            current = (indices1[i], indices2[i])
            if (prev[0] + 1) % len1 == current[0] and \
                                    (prev[1] + diff2) % len2 == current[1]:
                consensusLists[-1].append(current)
            else:
                consensusLists.append([current])

        # check for circular and index 0 in the middle of an intersection
        first = consensusLists[0][0]
        last = consensusLists[-1][-1]
        if (last[0] + 1) % len1 == first[0] and \
                                (last[1] + diff2) % len2 == first[1]:
            if len(consensusLists) == 1:
                # it's circular
                return consensusLists, True, reverse2
            else:
                # 0 is in middle of intersection
                consensusLists[0] = consensusLists[-1] + consensusLists[0]
                consensusLists.pop()
        return consensusLists, False, reverse2

    @staticmethod
    def _getBorderRegionIndices(points, intersection):
        """
        Returns:
            list of indices of points in points which are in intersection
        """
        indices = []
        for i, point in enumerate(points):
            if point in intersection:
                indices.append(i)
        return indices

    @staticmethod
    def _getIntersectingBorders(points1, points2):
        """
        Returns:
            list of lists of tuples which represents the aligned indices of points1 and points2 in each contiguous
            intersection of points1 and points2. Also returns whether the intersection is circular and whether points2
            is in reversed order.
            Ex: [[(pt1_0, pt2_0), (pt1_1, pt2_1), ...], [...]]
        """
        pointsSet1 = set(points1)
        pointsSet2 = set(points2)
        intersection = pointsSet1 & pointsSet2
        if intersection:
            pointsBorderIdxs1 = BorderProcessor._getBorderRegionIndices(points1, intersection)
            pointsBorderIdxs2 = BorderProcessor._getBorderRegionIndices(points2, intersection)

            # align lists, taking orientation into account
            searchPoint = points1[pointsBorderIdxs1[0]]
            offset = 0
            for i, index in enumerate(pointsBorderIdxs2):
                if searchPoint == points2[index]:
                    offset = i
                    break
            # check for direction
            reverse = False
            if len(pointsBorderIdxs1) > 1:
                tryIndex = (offset + 1) % len(pointsBorderIdxs2)
                if points2[pointsBorderIdxs2[tryIndex]] != points1[pointsBorderIdxs1[1]]:
                    reverse = True
            if reverse:
                # gnarly bug this one was
                # reversing the list means offsetting by one extra - set the new 0 pos at the end of the list
                # before reversing
                pointsBorderIdxs2 = np.roll(pointsBorderIdxs2, -offset - 1)
                pointsBorderIdxs2 = list(reversed(pointsBorderIdxs2))
            else:
                pointsBorderIdxs2 = np.roll(pointsBorderIdxs2, -offset)

            return BorderProcessor._getConsensusBorderIntersection(
                pointsBorderIdxs1, pointsBorderIdxs2, len(points1), len(points2), reverse
            )
        return [], False, False

    @staticmethod
    def _replaceIntoBorder(region, replace, start, stop, reverse=False):
        """
        Inserts the list replace between start and stop (counted inclusively) into the list region.
        Since the contiguous regions in _makeNewRegions are constructed using region1's vertices,
        a side effect of this method when region is region2 is to free region2's Vertex objects from memory.
        Args:
            region: The region to insert replace into
            replace: The list of Vertex objects to insert into region
            start: The start index (counted inclusively)
            stop: The end index (counted inclusively)
            reverse: Whether to treat replace, start, and stop in reversed order

        Returns:
            The new region (may be of different length than the input)
        """
        if reverse:
            replace = reversed(replace)
            start, stop = stop, start
        if stop < start:
            region = region[:start]
            region[:stop + 1] = replace
        else:
            region[start:stop + 1] = replace
        return region

    @staticmethod
    def _makeNewRegions(region1, region2):
        """
        Args:
            region1: One region represented by Vertex objects
            region2: Another region represented by Vertex objects
        Returns:
            region1 and region2 with their intersecting vertices modified
        """
        points1 = [(vertex.x, vertex.y) for vertex in region1]
        points2 = [(vertex.x, vertex.y) for vertex in region2]
        consensusLists, circular, reverse2 = BorderProcessor._getIntersectingBorders(points1, points2)
        processed = []
        for contiguous in consensusLists:
            # sanity check
            for indices in contiguous:
                assert points1[indices[0]] == points2[indices[1]]
            indices = zip(*contiguous)  # make separate lists for region1 and region2 coordinates
            processed.append(
                BorderProcessor._processVertices([region1[i] for i in indices[0]], circular)
            )
            assert len(indices[0]) == len(processed[-1])
        for i, contiguous in enumerate(processed):
            start = consensusLists[i][0][0]
            stop = consensusLists[i][-1][0]
            BorderProcessor._replaceIntoBorder(region1, contiguous, start, stop)
            start = consensusLists[i][0][1]
            stop = consensusLists[i][-1][1]
            BorderProcessor._replaceIntoBorder(region2, contiguous, start, stop, reverse2)
        return region1, region2

    @staticmethod
    def _makeRegionAdjacencyMatrixAndIndexKey(borders):
        """
        Returns:
            an adjacency matrix and a dictionary mapping group labels to indices
            (i.e., adjMatrix[indexKey[groupLabel] + regionIndex]
        """
        indexKey = {}
        n = 0
        for label in range(len(borders)):
            indexKey[label] = n
            n += len(borders[label])
        return np.zeros((n, n), dtype=np.int8), indexKey

    def process(self):
        """
        Returns:
            the borders object where the intersecting borders are made more natural
        """
        adjMatrix, indexKey = BorderProcessor._makeRegionAdjacencyMatrixAndIndexKey(self.borders)
        for groupLabel in self.borders:
            for regIdx, region in enumerate(self.borders[groupLabel]):
                regAdjIdx = indexKey[groupLabel] + regIdx
                for searchGroupLabel in self.borders:
                    if groupLabel is not searchGroupLabel:
                        for searchRegIdx, search_region in enumerate(self.borders[searchGroupLabel]):
                            searchRegAdjIdx = indexKey[searchGroupLabel] + searchRegIdx
                            if not adjMatrix[regAdjIdx][searchRegAdjIdx]:
                                self.borders[groupLabel][regIdx], \
                                    self.borders[searchGroupLabel][searchRegIdx] = \
                                    BorderProcessor._makeNewRegions(region, search_region)
                                adjMatrix[regAdjIdx][searchRegAdjIdx] = 1
                                adjMatrix[searchRegAdjIdx][regAdjIdx] = 1
        return self.borders
