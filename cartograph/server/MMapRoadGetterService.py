import falcon
import heapq
import json
from tables import*
import pandas as pd
import numpy as np
import math
import pytest
from collections import defaultdict

class PrioritySet(object):
    def __init__(self, max_size = 10):
        self.heap = []
        self.set = set()
        self.max_size = max_size


    def add(self,  pri, d):
        if not d in self.set:

            heapq.heappush(self.heap, (pri, d))
            self.set.add(d)
            if len(self.heap) > self.max_size:
                self.pop()

    def pop(self):
        pri, d = heapq.heappop(self.heap)
        self.set.remove(d)
        return d

    def add_all(self, list_to_add):
        for ele in list_to_add:
            self.add(ele[0], ele[1])

    def __str__(self):
        return str(self.heap)


class RoadGetterService:
    def __init__(self, links, origVertsPath, pathToZPop, pathToNames, outputdir):
        self.articlesZpop = {}  # here articlesZpop key is article ID, and val is a float zpop val
        with open(pathToZPop, "r") as zpop:
            for line in zpop:
                lst = line.split()
                if lst[0] == "index":
                    continue
                if lst[0] == "3019":
                    self.articlesZpop[int(lst[0])] = 12
                    continue
                self.articlesZpop[int(lst[0])] = math.ceil(float(lst[1]))+ 1

        sequence = createSequence(links, self.articlesZpop)
        writeSparseMatrix(sequence, outputdir)
        colAddress = outputdir + "/columns.mmap"
        rowAddress = outputdir + "/row_indexes.mmap"
        valAddress = outputdir + "/values.mmap"
        self.rowMap = np.memmap(rowAddress, dtype="int32", mode="r+")
        self.colMap = np.memmap(colAddress, dtype="int32", mode="r+")
        self.valMap = np.memmap(valAddress, dtype="int32", mode="r+")

        print(self.valMap)
        print(self.colMap)
        print(self.rowMap)
        pairs = [(4, 1247), (4, 39262), (5, 185), (5, 127), (7, 3), (7,635), (8, 2557), (8,39078), (10, 498), (10, 16736), (10, 75164), (2295, 35), (2295, 92) ]
        for src, dest in pairs:
            assert self.articlesZpop[src] * self.articlesZpop[dest] == self.get_row_as_dict(pointID=src)[dest]
        #This sets up all the variables we need for any work done.

        self.names = {}
        with open(pathToNames, "r") as namesFile:
            for line in namesFile:
                lst = line.split('\t')
                if lst[0] == "id": continue
                self.names[int(lst[0])] = lst[1]

        self.originalVertices = {}
        with open(origVertsPath) as ptov:
            for line in ptov:
                lst = line.split()
                if len(lst) == 1: continue
                self.originalVertices[int(lst[0])] = [float(lst[1]), float(lst[2])]

    def on_get(self, req, resp):
        #print("hehe ecks dee")
        edges = self.getPathsInViewPort(float(req.params['xmin']), float(req.params['xmax']),
                                        float(req.params['ymin']), float(req.params['ymax']),
                                        int(req.params['num_paths']))
        pathpairs = []
        for edge in edges:
            edge = list(edge)
            if len(edge) == 2:
                pathpairs.append(edge[1]) #should append [src, dest]
        paths = []
        pathsCovered = []
        bothWays = []
        for pair in pathpairs:
            src = int(pair[0])
            dest = int(pair[1])
            pathsCovered.append(pair)
            if ((dest, src) in pathsCovered):
                bothWays.append((src,dest))
                continue
            srcCord = self.originalVertices[src]  # both of the Cord vals are arrays [y,x]
            dstCord = self.originalVertices[dest]
            srcCord = [srcCord[1], srcCord[0]]
            dstCord = [dstCord[1], dstCord[0]]
            paths.append([int(src), self.names[src][:-1], srcCord])
            paths.append([int(dest), self.names[dest][:-1], dstCord])

        jsonDict  = {"paths":  paths, "bothWays": bothWays}

        print('len bw', bothWays)
        resp.status = falcon.HTTP_200
        resp.content_type = "application/json"  #getMimeType(file)
        #print(json.dumps(jsonDict))
        #print("len", len(json.dumps(jsonDict)))
        resp.body = json.dumps(jsonDict)

    def get_row_as_dict(self, index=-1, pointID = -1):
        if pointID != -1:
            index = pointID - 1
        else:
            if pointID == -1 and index == -1:
                print("Error, please specify index or edgeId value")

        startIndex = self.rowMap[index]
        endIndex = self.rowMap[index+1]

        edgeValDict = {}
        for i in range(startIndex, endIndex):
            edgeValDict[self.colMap[i]] = self.valMap[i]
        return edgeValDict

    #hopefully properly implemented
    def getPathsInViewPort(self, xmin, xmax, ymin, ymax, num_paths):
        pointsinPort = []
        for point in self.originalVertices:
            if xmax > float(self.originalVertices[point][0]) > xmin and ymin < float(self.originalVertices[point][1]) < ymax:
                pointsinPort.append(point)  # points in port is an array of pointIDs which are strings.
        topPaths = PrioritySet(max_size=num_paths)
        #This part above shouldn't conflict with anything from the sparse matrix. The part below should.
        good = []
        bad = []
        diff=[]
        for src in pointsinPort:
            if src < len(self.rowMap):
                destDict = self.get_row_as_dict(pointID=src)
                for dest in destDict:
                    if dest in self.originalVertices and xmax > self.originalVertices[dest][0] > xmin and ymax > self.originalVertices[dest][1] > ymin:
                        secondVal = destDict[dest]
                        topPaths.add(-secondVal, (src, dest))
        return topPaths.heap

def createSequence(links, zpop):
    sequenceDict = defaultdict(dict) #yeah I know this isn't efficient but I just need something to test
    with open(links, 'r') as ptbe:
        for line in ptbe:
            lst = line.split()
            if lst[0] == "id": continue
            src = int(lst[0])
            sequenceDict[src] = {}
            for dest in lst[1:]:
                sequenceDict[src][int(dest)] = zpop[src]*zpop[int(dest)]

    sequenceList = []
    for key in sorted(sequenceDict): #sorting here preserves order, uhh yeah.
        sequenceList.append((key, sequenceDict[key]))
    return sequenceList #This should be hopefully the set of tuples, (row, vals) where val is a dictionary with weight vals

def writeSparseMatrix(sequence, outputdir):
    count = 0
    rows = []
    cols = []
    vals = []
    for pairing in (sequence):
        src, roadDict = pairing
        for dest in sorted(roadDict):
            cols.append(dest)
            vals.append(roadDict[dest])
        rows.append(count)
        count += len(roadDict)
    #rows memmap conversion here rows are set so pointID is the index (to get the row value of point 12, go to row[12]
    #from there the value yielded is the row's start and end lines in our text file. for example point1 is from 0 to point2's start
    rowNp = np.asarray(rows)
    rowShape = rowNp.shape
    rowMap = np.memmap(outputdir+"/row_indexes.mmap", dtype='int32', mode="w+", shape=rowShape)
    rowMap[:] = rowNp
    rowMap.flush()

    #cols mmap conversion. Cols stores the given pointID at an index value. for example, if at index 12, we had an edge between 1 and 54, cols[12] = 54
    colNp = np.asarray(cols)
    colShape = colNp.shape
    colMap = np.memmap(outputdir+"/columns.mmap", dtype='int32', mode="w+", shape=colShape)
    colMap[:] = colNp
    colMap.flush()

    #vals mmap conversion this stores the weight for a given index.
    valNp = np.asarray(vals)
    valShape = valNp.shape
    valMap = np.memmap(outputdir+"/values.mmap", dtype="int32", mode="w+", shape=valShape)
    valMap[:] = valNp
    valMap.flush()

    #draw Shapes!
    shapesFile = open(outputdir+"shape.txt", "w")
    shapesFile.write(str(len(rows))+" "+str(len(rows)))
    shapesFile.close()