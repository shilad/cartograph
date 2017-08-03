import csv
from pyqtree import Index
from MMapRoadGetterService import PrioritySet
from cartograph.mmap_matrix import MMappedSparseMatrix as mmap

import time
import cPickle as pickle
import os
import random
import numpy as np


class VerticeQuadTree():

    def __init__(self, origVertsPath, edgesMmapPath):

        self.originalVertices = {}
        self.max_x = 0
        self.min_x = 0
        self.max_y = 0
        self.min_y = 0
        self.maxNumberOfEdges = 200
        self.edgesMMap = mmap.MMappedSparseMatrix(edgesMmapPath)
        coorPathFile = edgesMmapPath + 'pickledVertices.pickle'
        self.readCoordinatesFile(origVertsPath, coorPathFile)
        self.quadTreeVertices = None
        treePath = edgesMmapPath + 'verticesQuadTree.pickle'
        self._populateTree(treePath)


    def readCoordinatesFile(self, origVertsPath, pathForPickledFile):
        '''
        This method creates a dictionary where the key is the article id and the
        value a tuple of x, y coordinates. It also finds the min and max x, y
        coordinates for the data set.
        :param origVertsPath: path where the input file with articles coordinates are
        :param pathForPickledFile: path where the pickled file should be saved
        :return:
        '''
        if (os.path.isfile(pathForPickledFile)):
            with open(pathForPickledFile, "rb") as pickledDict:
                try:
                    treeInfo = pickle.load(pickledDict)
                    self.min_x = treeInfo[0]
                    self.min_y = treeInfo[1]
                    self.max_x = treeInfo[2]
                    self.max_y = treeInfo[3]
                    self.originalVertices = treeInfo[4]

                except StandardError:

                    pass
        else:
            with open(origVertsPath) as ptov:
                tabCoordinates = csv.reader(ptov, delimiter='\t')
                for row in tabCoordinates:
                    if row[0] == 'index': continue
                    id = int(row[0])
                    x = float(row[1])
                    y = float(row[2])
                    self.originalVertices[id] = (x, y)
                    if x > self.max_x:
                        self.max_x = x
                    elif x < self.min_x:
                        self.min_x = x
                    if y > self.max_y:
                        self.max_y = y
                    elif y < self.min_y:
                        self.min_y = y
            with open(pathForPickledFile, 'wb') as pickledDict:
                toDump = (self.min_x, self.min_y, self.max_x, self.max_y, self.originalVertices)
                pickle.dump(toDump, pickledDict)


    def _populateTree(self, path):
        '''
        This method creates the quad tree that contains the the article Ids and calls a helper method to create the
        priority queue for each of the leaves with the most important edges
        :param path:
        :return:
        '''
        if(os.path.isfile(path)):
            with open(path,"rb") as pickledTree:
                try:
                    self.quadTreeVertices = pickle.load(pickledTree)
                except StandardError:
                    pass
        else:
            self.quadTreeVertices = Index(bbox=(self.min_x, self.min_y, self.max_x, self.max_y), maxitems=20)
            for vertex in self.originalVertices:
                x = self.originalVertices[vertex][0]
                y = self.originalVertices[vertex][1]
                self.quadTreeVertices.insert(vertex, bbox=(x, y, x, y))
            self._setEdgesForQuad(self.quadTreeVertices)
            with open(path, 'wb') as pickledTree:

                pickle.dump(self.quadTreeVertices, pickledTree)


    def _getQuadChildrenInViewPort(self, xmin, ymin, xmax, ymax, quad, results = None):
        '''
        This is a helper method that finds the leaves in the quad tree that are at least in part
         within the view port. This  method is based on the _intersect method of the QuadTree class
        :param xmin: minimum x coordinate in the view port
        :param ymin: minimum y coordinate in the view port
        :param xmax: maximum x coordinate in the view port
        :param ymax: maximum y coordinate in the view port
        :param quad: a quad tree
        :param results: the list of results
        :return: a list of the quad tree leaves that are  at least in part
         within the view port
        '''
        rect = (xmin, ymin, xmax, ymax)
        if results is None:
            results = []
        # search children
        if len(quad.children) > 0:
            if rect[0] <= quad.center[0]:
                if rect[1] <= quad.center[1]:
                    self._getQuadChildrenInViewPort(xmin, ymin, xmax, ymax, quad.children[0], results=results)
                if rect[3] > quad.center[1]:
                    self._getQuadChildrenInViewPort(xmin, ymin, xmax, ymax, quad.children[1], results=results)
            if rect[2] > quad.center[0]:
                if rect[1] <= quad.center[1]:
                    self._getQuadChildrenInViewPort(xmin, ymin, xmax, ymax, quad.children[2], results=results)
                if rect[3] > quad.center[1]:
                    self._getQuadChildrenInViewPort(xmin, ymin, xmax, ymax, quad.children[3], results=results)
        # search node at this level
        if len(quad.nodes) != 0:
            results.append(quad)
        return results

    def getKMostProminentEdgesInViewPort(self, xmin, ymin, xmax, ymax, k=100):
        '''
        This method returns a Priority Set with the K most prominent edges in the view port
        :param xmin:
        :param ymin:
        :param xmax:
        :param ymax:
        :param k:
        :return:
        '''
        if k > self.maxNumberOfEdges:
            k = self.maxNumberOfEdges
        quadChildren = self._getQuadChildrenInViewPort(xmin, ymin, xmax, ymax, self.quadTreeVertices)

        edges = PrioritySet(max_size=k)

        for quad in quadChildren:
            if self.isViewPortSmallerThanLeaf(quad, xmin, ymin, xmax, ymax):
                return bruteForceEdges(xmin, ymin, xmax, ymax, self.originalVertices, k, self.edgesMMap )

            for edgeInfo in quad.mostImportantEdgeSet.priorityValueResults:
                if(edgeInfo[0] >= edges.maxImportance): break

                if not self.sourceInInViewPort(edgeInfo[1][0], xmin, ymin, xmax, ymax): continue
                edges.add(edgeInfo[0], edgeInfo[1])

        return edges

    def isViewPortSmallerThanLeaf(self, quad, xmin, ymin, xmax, ymax):
        '''
        This method checks if the viewport fits completely within a leaf
        :param quad:
        :param xmin:
        :param ymin:
        :param xmax:
        :param ymax:
        :return: True if the viewport fits completely within a leaf, false otherwise
        '''
        quadXmin = quad.center[0] - quad.height / 2
        quadXmax = quad.center[0] + quad.height / 2
        quadYmin = quad.center[1] - quad.width / 2
        quadYmax = quad.center[1] + quad.width / 2

        if xmin > quadXmin and xmax < quadXmax and ymin > quadYmin and ymax < quadYmax:


            return True

        else:
            return False



    def sourceInInViewPort(self, sourceId, xmin, ymin, xmax, ymax ):
        '''
        This method checks if the article identified by SourceId is within the viewport
        :param sourceId:
        :param xmin:
        :param ymin:
        :param xmax:
        :param ymax:
        :return: True if the article is within the viewport, false otherwise
        '''
        sourceCoor = self.originalVertices[sourceId]

        if xmax >= sourceCoor[0] >= xmin and ymin <= sourceCoor[1] <= ymax:
            return True
        return False


    def _setEdgesForQuad(self, quad):
        '''
        Recursive method that adds a priority queue to the leaves of the quad tree.
        The priority queue contain the k most important edges for that leaf.
        :param quad: a quad tree
        :return:
        '''
        if len(quad.nodes) != 0:

            quad.mostImportantEdgeSet = PrioritySet(max_size=self.maxNumberOfEdges)
            for node in quad.nodes:
                srcId = node.item
                srcEdges = self.edgesMMap.get_row_as_dict(pointID=srcId)
                for dest in srcEdges:

                    quad.mostImportantEdgeSet.add(srcEdges[dest], (srcId, dest))


        else:
            for child in quad.children:
                self._setEdgesForQuad(child)


#### Below are methods for testing/benchmark
def createRandomDict(maxNumber):
    maxEdgeNum = 500
    dictSize = random.randint(0, min(maxNumber, maxEdgeNum))
    outPutDict = {}

    for i in range(dictSize):
        index = random.randint(0, maxNumber)
        outPutDict[index] = random.uniform(0, maxNumber*100)
    return  outPutDict

def createRandomSequence(size):
    sequence = []
    coor = {}


    for i in range(size):
        dictionary = createRandomDict(size)
        sequence.append((i, dictionary))
        x = random.uniform(-40.0, 40.0)
        y = random.uniform(-40.0, 40.0)
        coor[i] = (x, y)
    # sequence = [(1, {2: 8, 11: 3}), (2, {12: 4, 13: 6, 14: 0}), (3, {4:4}),(4, {3: 7, 20: 9, 18: 1, 17: 16}),
    #              (5, {7: 1}), (6, {9: 0, 19: 5}), (7, {1: 2, 4: 3}), (8, {13: 5}), (9, {2: 9}),
    #              (10, {6: 1}), (11, {10: 4}), (12, {4: 6, 2: 0}), (13, {9: 5}), (14, {15: 2}),
    #              (15, {19: 7, 20: 8}), (16, {11: 2, 6: 9, 5: 3}), (17, {12: 8, 6: 1}), (18, {13: 10, 4: 3, 1: 7}),
    #              (19, {15: 0, 9
    # : 10}), (20, {19: 6, 3: 2, 8:4})]
    # coor = {1: (7, 1), 2: (6, 3), 3: (6, 3), 4: (14, 2), 5: (11, 3), 6: (9, 4), 7: (3, 6), 8: (7, 6), 9: (12, 6),
    #          10: (13, 7),
    #          11: (9, 8), 12: (5, 10), 13: (2, 12), 14: (10, 12), 15: (13, 10), 16: (5, 13), 17: (2, 15), 18: (9, 15),
    #          19: (13, 15), 20: (2, 4)}
    return sequence, coor


def test_VerticesQuadTree():
    clearTestFiles('/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/')
    sequence, coor = createRandomSequence()
    writeDictToFile('/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/test_vertices_coordinates.tsv', coor)
    mmap.writeSparseMatrix(sequence, '/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/')
    vqt = VerticeQuadTree('/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/test_vertices_coordinates.tsv', '/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/' )
    differentSize = 0
    totalDifferentce = 0
    total = 100
    countAllInBoth = 0
    countNotAllInBoth = 0
    totalSame = 0
    totalNotInBruteForce= 0
    for i in range(total):
        xs = (random.uniform(vqt.min_x, vqt.max_x), random.uniform(vqt.min_x, vqt.max_x))
        ys = (random.uniform(vqt.min_y, vqt.max_y), random.uniform(vqt.min_y, vqt.max_y))
        x_min = min(xs)
        x_max = max(xs)
        y_min = min(ys)
        y_max = max(ys)
        resultsTree = vqt.getKMostProminentEdgesInViewPort(x_min, y_min, x_max, y_max, k=100)
        resultsBruteForce = bruteForceEdges(x_min, y_min, x_max, y_max, vqt.originalVertices, 100, vqt.edgesMMap)

        #assert len(resultsTree.priorityValueResults) == len(resultsBruteForce)

        if len(resultsTree) != len(resultsBruteForce):
            totalDifferentce += abs(len(resultsBruteForce)-len(resultsTree))
            differentSize += 1
        else:
            totalSame += 1

        countInBothFirst = 0
        countNotInBrute = 0

        for result in resultsTree.priorityValueResults:
            if result not in resultsBruteForce.priorityValueResults:
                   # print 'result not in bruteForce', result
                    #print resultsTree
                    #print resultsBruteForce
                countNotInBrute +=1
            else: countInBothFirst += 1
        totalNotInBruteForce += countNotInBrute
        if countNotInBrute == 0:
            countAllInBoth += 1
        else:
            countNotAllInBoth += 1
    print "Different size:", differentSize,  ", Same size:", totalSame, ", % of total different size:", float(differentSize)/float(total)
    if differentSize != 0: print "Avg Difference:", float(totalDifferentce)/float(differentSize)
    print  "Not All in Both:", countNotAllInBoth, ", All in Both:", countAllInBoth, ", % of total of not all in both:", float(countNotAllInBoth)/float(total)
    if countNotAllInBoth != 0: print "Avg different from brute force:", totalNotInBruteForce/countNotAllInBoth
def clearTestFiles(pathToDir):
    dir = pathToDir
    test = os.listdir(dir)
    for item in test:
        if item.endswith(".pickle") or item.endswith(".mmap") or item.endswith(".tsv") or item.endswith(".txt"):
            os.remove(os.path.join(dir, item))

def writeDictToFile(path, dictionary):
    with open(path, 'wb') as pathToFile:
        writ = csv.writer(pathToFile, delimiter = '\t')
        for key in dictionary:
            row = [key, dictionary[key][0], dictionary[key][1]]
            writ.writerow(row)

def bruteForceEdges(xmin, ymin, xmax, ymax, originalVertices, num_paths, sparsematrix):
    pointsinPort = []
    for point in originalVertices:
        if xmax >= float(originalVertices[point][0]) >= xmin and ymin <= float(
                originalVertices[point][1]) <=ymax:
            pointsinPort.append(point)  # points in port is an array of pointIDs which are strings.
    topPaths = PrioritySet(max_size=num_paths)

    for src in pointsinPort:
        # if src < len(self.rowMap):
        destDict = sparsematrix.get_row_as_dict(pointID=src)
        for dest in destDict:

            secondVal = destDict[dest]
            topPaths.add(secondVal, (src, dest))
    return topPaths


#test_VerticesQuadTree()




def benchmark():
    clearTestFiles('/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/')
    createDictStart = time.time()
    sequence, coor = createRandomSequence(2000000)
    createDictFinish = time.time()
    print "Done creating dicts, time =", createDictFinish - createDictStart
    writeDictToFile('/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/test_vertices_coordinates.tsv',
                    coor)
    createMMapStart = time.time()
    mmap.writeSparseMatrix(sequence, '/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/')
    createMMapFinish = time.time()

    print "Done creating mmap, time =", createMMapFinish - createMMapStart
    createQuadTreeStart = time.time()
    vqt = VerticeQuadTree(
        '/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/test_vertices_coordinates.tsv',
        '/Users/sen/PycharmProjects/cartographEdges/cartograph/mmap_matrix/')
    createQuadTreeFinish = time.time()
    print "Done creating quad tree, time =",  createQuadTreeFinish - createQuadTreeStart
    times = []
    for i in range(1000):
        xs = (random.uniform(vqt.min_x, vqt.max_x), random.uniform(vqt.min_x, vqt.max_x))
        ys = (random.uniform(vqt.min_y, vqt.max_y), random.uniform(vqt.min_y, vqt.max_y))
        x_min = min(xs)
        x_max = max(xs)
        y_min = min(ys)
        y_max = max(ys)
        calcGetEdges = time.time()
        results = vqt.getKMostProminentEdgesInViewPort(x_min, y_min, x_max, y_max, k=100)
        finishGetCalcEdges = time.time()
        times.append(finishGetCalcEdges-calcGetEdges)


    print 'time =', np.mean(times)

#--- "Memory problems, but works well with a million" ----

#benchmark()
