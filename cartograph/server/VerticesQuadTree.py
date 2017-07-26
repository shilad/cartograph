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

    def __init__(self, origVertsPath):

        self.originalVertices = {}
        self.max_x = 0
        self.min_x = 0
        self.max_y = 0
        self.min_y = 0
        self.maxNumberOfEdges = 200
        self.edgesMMap = mmap.MMappedSparseMatrix("/Users/sen/PycharmProjects/cartograph/data/ext/simple/")
        self.readCoordinatesFile(origVertsPath,'pickledVertices.pickle')
        self.quadTreeVertices = None
        self._populateTree('verticesQuadTree.pickle')



    def readCoordinatesFile(self, origVertsPath, pathForPickledFile):
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
        if(os.path.isfile(path)):
            with open(path,"rb") as pickledTree:
                try:
                    self.quadTreeVertices = pickle.load(pickledTree)
                except StandardError:
                    pass
        else:
            self.quadTreeVertices = Index(bbox=(self.min_x, self.min_y, self.max_x, self.max_y), maxitems=100)
            for vertex in self.originalVertices:
                x = self.originalVertices[vertex][0]
                y = self.originalVertices[vertex][1]
                self.quadTreeVertices.insert(vertex, bbox=(x, y, x, y))
            self._getEdgesForQuad(self.quadTreeVertices)
            with open(path, 'wb') as pickledTree:

                pickle.dump(self.quadTreeVertices, pickledTree)


    def _getQuadChildrenInViewPort(self, xmin, ymin, xmax, ymax, quad, results = None):
        rect = (xmin, ymin, xmax, ymax)
        if results is None:
            results = set()
        if len(quad.nodes) != 0:
            results.add(quad)
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
        return results

    def getKMostProminentEdgesInViewPort(self, xmin, ymin, xmax, ymax, k=100):
        if k > self.maxNumberOfEdges:
            k = self.maxNumberOfEdges
        quadChildren = self._getQuadChildrenInViewPort(xmin, ymin, xmax, ymax, self.quadTreeVertices)
        edges = PrioritySet(max_size=k)

        for quad in quadChildren:
            #print quad.mostImportantEdgeSet
           for edgeInfo in quad.mostImportantEdgeSet.priorityValueResults:

                if(edgeInfo[0] >= edges.maxImportance): break
                edges.add(edgeInfo[0], edgeInfo[1])
        return edges

    def _getEdgesForQuad(self, quad):
        if len(quad.nodes) != 0:
            quad.mostImportantEdgeSet = PrioritySet(max_size=self.maxNumberOfEdges)
            for node in quad.nodes:
                srcId = node.item
                srcEdges = self.edgesMMap.get_row_as_dict(pointID=srcId)
                for dest in srcEdges:
                    quad.mostImportantEdgeSet.add(srcEdges[dest], (srcId, dest))
        else:
            for child in quad.children:
                self._getEdgesForQuad(child)



def benchmark():
    vqt = VerticeQuadTree('/Users/sen/PycharmProjects/cartographEdges/data/simple/tsv/coordinates.tsv')
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
        if i % 10 == 0:
            print x_min, y_min, x_max, y_max
            print results

    print 'time', np.mean(times)
#
# buildStart = datetime.datetime.now()
# vqt = VerticeQuadTree('/Users/sen/PycharmProjects/cartographEdges/data/simple/tsv/coordinates.tsv')
# buildFinish = datetime.datetime.now()
# buildTime = buildFinish-buildStart
# print 'buildTime', buildTime
#
# searchWholeViewPortStart = datetime.datetime.now()
# setVer= vqt.quadTreeVertices.intersect(bbox=(-40,-40,40,40))
# searchWholeViewPortFinish = datetime.datetime.now()
# print 'searchTime', searchWholeViewPortFinish - searchWholeViewPortStart
#
#
# calcGetEdges = datetime.datetime.now()
# result = vqt.getKMostProminentEdgesInViewPort(-40, -40, 40, 40,k=1)
# results = vqt.getKMostProminentEdgesInViewPort(-40, -40, 40, 40,k=10)
# results1 = vqt.getKMostProminentEdgesInViewPort(-40, -40, 40, 40,k=100)
# results2 = vqt.getKMostProminentEdgesInViewPort(-40, -40, 40, 40,k=200)
# results3 = vqt.getKMostProminentEdgesInViewPort(-40, -40, 40, 40,k=2)
# finishGetCalcEdges = datetime.datetime.now()
# print 'GetEdgesInViewPort', finishGetCalcEdges - calcGetEdges
# print result.priorityValueResults
# print results.priorityValueResults
# print results1.priorityValueResults
# print results2.priorityValueResults
# print results3.priorityValueResults

benchmark()