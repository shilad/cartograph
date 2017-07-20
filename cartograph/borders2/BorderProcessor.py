import numpy as np
from Noiser import NoisyEdgesMaker
from collections import defaultdict

class BorderProcessor:
    def __init__(self, borders, blurRadius, minBorderNoiseLength, waterLabel, points = {}, lines = {}, rings = {}, regions = {}):
        self.borders = borders
        self.blurRadius = blurRadius
        self.minBorderNoiseLength = minBorderNoiseLength
        self.waterLabel = waterLabel
        self.noise = False
        self.points = points
        self.lines = lines
        self.rings = rings
        self.regions = regions
        self.idGenerator = NewIDGenerator()
        self.processedLines = defaultdict(list)

    @staticmethod
    def wrapRange(start, stop, length, reverse=False):
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

    def blur(self, array, circular, radius):
        # arrays which are shorter than this will be blurred to a single point
        if len(array) <= radius * 2 + 1:
            return array
        blurred = []
        if circular:
            for i, _ in enumerate(array):
                start = i - radius
                stop = i + radius
                neighborhood = [
                    array[j] for j in self.wrapRange(start, stop, len(array))]
                blurred.append(np.average(neighborhood))
        else:
            for i, _ in enumerate(array):
                start = max(0, i - radius)
                stop = min(len(array) - 1, i + radius)
                neighborhood = [array[j] for j in range(start, stop + 1)]
                blurred.append(np.average(neighborhood))
        return blurred

    def processVertices(self, vertices, circular):
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
        if self.noise:
            # these vertices are on the coast
            vertices = NoisyEdgesMaker(vertices, self.minBorderNoiseLength).makeNoisyEdges(circular)
        else:
            x = [vertex.x for vertex in vertices]
            y = [vertex.y for vertex in vertices]
            x = self.blur(x, circular, self.blurRadius)
            y = self.blur(y, circular, self.blurRadius)
            for i, vertex in enumerate(vertices):
                vertex.x = x[i]
                vertex.y = y[i]
        return vertices

    def processVertices_new(self, commonPoints, circular):
        if len(commonPoints) < 2:
            return commonPoints
        if self.noise:
            commonPoints, self.points = NoisyEdgesMaker(commonPoints, self.minBorderNoiseLength).makeNoisyEdges_new(commonPoints, self.points,
                                                                                        circular, self.idGenerator)
        else:
            coordinates = []
            idOrder = []
            for pointId in commonPoints:
                idOrder.append(pointId)
                coordinates.append(self.getCoordinatesOfPointId(pointId))
            x, y = zip(*coordinates)
            x = self.blur(x, circular, self.blurRadius)
            y = self.blur(y, circular, self.blurRadius)
            for i, pointId in enumerate(idOrder):
                self.points[pointId] = (x[i], y[i]) + self.points[pointId][2:]
        return commonPoints

    @staticmethod
    def getConsensusBorderIntersection(indices1, indices2, len1, len2, reverse2):
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
            raise ValueError("Lists of indices must be the same length. There are probably double instances of "
                             "vertices in the lists.")

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
                # 0 is in middle of intersection (i.e., the first and last "look" like non-contiguous segments,
                # but they are in reality connected
                consensusLists[0] = consensusLists.pop() + consensusLists[0]
        return consensusLists, False, reverse2

    @staticmethod
    def getBorderRegionIndices(points, intersection):
        """
        Returns:
            list of indices of points in points which are in intersection
        """
        indices = []
        for i, point in enumerate(points):
            if point in intersection:
                indices.append(i)
        return indices

    def getIntersectingBorders(self, points1, points2):
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
            pointsBorderIdxs1 = self.getBorderRegionIndices(points1, intersection)
            pointsBorderIdxs2 = self.getBorderRegionIndices(points2, intersection)

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

            return self.getConsensusBorderIntersection(
                pointsBorderIdxs1, pointsBorderIdxs2, len(points1), len(points2), reverse
            )
        return [], False, False

    def makeNewRegionFromProcessed(self, region, processedVertices, regionStartStopList, reverse=False, new = False):
        '''What is this doing??? '''
        assert len(processedVertices) == len(regionStartStopList)
        if reverse:
            # reverse both startStopList and processed vertices (both inner and outer lists)
            regionStartStopList = [list(reversed(startStop)) for startStop in reversed(regionStartStopList)]
            processedVertices = [list(reversed(contiguous)) for contiguous in reversed(processedVertices)]
        processedRegion = []
        index = 0
        startStopListIndex = 0
        # find the section that overlaps 0 (if any) and move it to the back of the list
        # also move the start index to 1 more than the end of the overlapping region
        for i, startStop in enumerate(regionStartStopList):
            if startStop[0] > startStop[1]:
                regionStartStopList = np.roll(regionStartStopList, -i - 1, axis=0)
                processedVertices = np.roll(processedVertices, -i - 1, axis=0)
                index = startStop[1] + 1
                break
        # now that everything is in order, find the section with the smallest start value and move to to the front
        # this will only be necessary if there were no regions overlapping 0
        smallestStartValIndex = np.argmin(regionStartStopList, axis=0)[0]
        regionStartStopList = np.roll(regionStartStopList, -smallestStartValIndex, axis=0)

        processedVertices = np.roll(processedVertices, -smallestStartValIndex, axis=0)
        while index < len(region):
            if startStopListIndex < len(regionStartStopList) and index == regionStartStopList[startStopListIndex][0]:
                if new:
                    processedVertices[startStopListIndex][0] = int(processedVertices[startStopListIndex][0])
                    try:

                        processedVertices[startStopListIndex][-1] = int(processedVertices[startStopListIndex][-1])
                    except ValueError:
                        pass
                processedRegion.extend(processedVertices[startStopListIndex])
              #  print 'procvert', type(processedVertices[startStopListIndex][0])
                start, stop = regionStartStopList[startStopListIndex]
                index += len(self.wrapRange(start, stop, len(region)))
                startStopListIndex += 1
            else:
                processedRegion.append(region[index])
              #  print 'reg', region[index]
                index += 1

        return processedRegion

    def makeNewRegions(self, region1, region2):
        """
        Args:
            region1: One region represented by Vertex objects
            region2: Another region represented by Vertex objects
        Returns:
            new regions with their intersecting points modified
        """
        # print('a lens are ', len(region1), 'to', len(region2))
        points1 = [(vertex.x, vertex.y) for vertex in region1]
        points2 = [(vertex.x, vertex.y) for vertex in region2]
        consensusLists, circular, reverse2 = self.getIntersectingBorders(points1, points2) #What reverse means?

        if len(consensusLists) == 0:
            return region1, region2

        region1StartStopList = []
        region2StartStopList = []
        processed = []
       # print(circular)
        for contiguous in consensusLists:
            # sanity check
            #print('contiguous', contiguous)
            for indices in contiguous:

                assert points1[indices[0]] == points2[indices[1]]
            indices = zip(*contiguous)  # make separate lists for region1 and region2 coordinates
           # print(indices)
            region1StartStopList.append((indices[0][0], indices[0][-1]))
            region2StartStopList.append((indices[1][0], indices[1][-1]))
            processed.append(
                self.processVertices([region1[i] for i in indices[0]], circular)
            )
       # print 'processed', processed
        processedRegion1 = self.makeNewRegionFromProcessed(region1, processed, region1StartStopList)
        processedRegion2 = self.makeNewRegionFromProcessed(region2, processed, region2StartStopList, reverse2)
        # print('b, from', len(region1), 'to', len(processedRegion1))
        # print('c, from', len(region2), 'to', len(processedRegion2))

        return processedRegion1, processedRegion2

    def makeNewRegion_new(self, ring1, ring2):
        consensusLists, circular, reverse2 =self.getIntersectingBorders(ring1, ring2)

        if len(consensusLists) == 0:
            return ring1, ring2
        processed = []
        region1StartStopList = []
        region2StartStopList = []

        for contiguous in consensusLists:
            # sanity check
            #print('contiguous', contiguous)
            for indices in contiguous:

                assert ring1[indices[0]] == ring2[indices[1]]
            indices = zip(*contiguous)  # make separate lists for region1 and region2 coordinates
            ringsId= [ring1[i] for i in indices[0]]
            ring1pointsID = []
            for id in ringsId:
                #pass
               ring1pointsID.extend(self.lines[id])
            region1StartStopList.append((indices[0][0], indices[0][-1]))
            region2StartStopList.append((indices[1][0], indices[1][-1]))
            processed.append(
                self.processVertices_new(ring1pointsID, circular)
            )
        ringsId2 = [ring2[i] for i in indices[1]]
        ring2pointsID = []
        for id in ringsId2:
            # pass
            ring2pointsID.extend(self.lines[id])
        processedRing1 = self.makeNewRegionFromProcessed(ring1pointsID, processed, region1StartStopList, new = True)
        processedRing2 = self.makeNewRegionFromProcessed(ring2pointsID, processed, region2StartStopList, reverse2, new = True)

        ring1 = self.makeLineDictOutOFNewPointDict(processedRing1, self.idGenerator)
        ring2 = self.makeLineDictOutOFNewPointDict(processedRing2, self.idGenerator)
      #  print 'p1', processedRing1
      #  print 'p2', processedRing2
        return ring1, ring2

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
                #print (previous, newPointId)
            previous = newPointId
            pair += 1
        return newLinesID


    def getCoordinatesOfPointId(self, pointId):
        coordinates = self.points[pointId][:2]
        return coordinates

    def getIsOnCoastOfPointId(self, pointId):
        IsOnCoast = self.points[pointId][2]
        return IsOnCoast

    def getRegionPointsOfPointId(self, pointId):
        regionPoints = self.points[pointId][3]
        return regionPoints

    def process(self):
        """
        Returns:
            the borders object where the intersecting borders are made more natural
        """
        regionIds = []
        for group in self.borders:
            regionIds.extend((group, i) for i in range(len(self.borders[group])))
        print('regions', regionIds)
        print 'borders', self.borders
        for (group1, i) in regionIds:
            for (group2, j) in regionIds:
                if group1 < group2:
                        self.noise = group2 == self.waterLabel
                        self.borders[group1][i], self.borders[group2][j] = \
                            self.makeNewRegions(self.borders[group1][i], self.borders[group2][j])
        self.process_new()


        return self.borders

    def process_new(self):
        regionIds = []
        for key in self.regions: #key = clusterId
            regionIds.extend((key, i) for i in range(len(self.regions[key])))
        print 'regions2', regionIds
        for (cluster1, i) in regionIds:
            for (cluster2, j) in regionIds:
                if cluster1 < cluster2:
                    self.noise = cluster2 == self.waterLabel

                    ring1 =  self.rings[self.regions[cluster1][i]] #self.getPointIDForRing(self.regions[cluster1][i])
                    ring2 = self.rings[self.regions[cluster2][j]] #self.getPointIDForRing(self.regions[cluster2][j]) #

                    #print 'ring1', ring1
                    #print 'ring2', ring2
                    ring1 , ring2 = self.makeNewRegion_new(ring1, ring2)
                    ring1ID = 'n' + str(self.idGenerator.getNextID())
                    self.rings[ring1ID] = ring1
                    ring2Id = 'n' + str(self.idGenerator.getNextID())
                    self.rings[ring2Id] = ring2


                    self.regions[cluster1][i] = ring1ID
                    self.regions[cluster2][j] = ring2Id

        self.checkThings()



        return self.points, self.lines, self.rings, self.regions

    def getPointIDForRing(self, ringId):
        lines = self.rings[ringId]
        pointsID = []
        for lineID in lines:
            points = self.lines[lineID]
            pointsID.extend(points)
        return pointsID

    def checkThings(self):
        for regionId in self.regions:
            for ringId in self.regions[regionId]:
                #print 'ring', ringId, self.rings[ringId]
                for lineId in self.rings[ringId]:
                    #print 'line', lineId, self.lines[lineId]
                    for pointID in self.lines[lineId]:
                        if pointID in self.points:
                          pass
                          #  print 'point', pointID, self.points[pointID]
                           # print type(pointID)
                        else:

                            print 'no', pointID, type(pointID)


class NewIDGenerator():

    def __init__(self):
        self.lastID = 0

    def getNextID(self):

        self.lastID += 1
        return self.lastID

