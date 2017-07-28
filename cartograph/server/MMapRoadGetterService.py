import falcon
import heapq
import json
import math
from collections import defaultdict
import bisect
import numpy as np

from cartograph.mmap_matrix import MMappedSparseMatrix as mmap
class PrioritySet(object):
    def __init__(self, max_size = 10):
        self.keys = []

        self.max_size = max_size
        self.maxImportance = float('inf')
        self.priorityValueResults= [] #value (priority, value)


    def add(self,  pri, d):
        if pri <= self.maxImportance:
            index = bisect.bisect_right(self.keys,pri)
            if index == self.max_size: return
            self.priorityValueResults.insert(index,(pri, d))
            self.keys.insert(index, pri)

            if len(self.keys) > self.max_size:
                self.keys = self.keys[:-1]
                self.priorityValueResults = self.priorityValueResults[:-1]
                self.maxImportance = self.keys[-1]

    def add_all(self, list_to_add):
        for ele in list_to_add:
            self.add(ele[0], ele[1])

    def __str__(self):
        return str(self.priorityValueResults)

    def __len__(self):
        return len(self.priorityValueResults)


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
        mmap.writeSparseMatrix(sequence, outputdir)
        self.sparsematrix = mmap.MMappedSparseMatrix(outputdir)
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

    #hopefully properly implemented
    def getPathsInViewPort(self, xmin, xmax, ymin, ymax, num_paths):
        pointsinPort = []
        for point in self.originalVertices:
            if xmax > float(self.originalVertices[point][0]) > xmin and ymin < float(self.originalVertices[point][1]) < ymax:
                pointsinPort.append(point)  # points in port is an array of pointIDs which are strings.
        topPaths = PrioritySet(max_size=num_paths)

        for src in pointsinPort:
            #if src < len(self.rowMap):
            destDict = self.sparsematrix.get_row_as_dict(pointID=src)
            for dest in destDict:
                if dest in self.originalVertices and xmax > self.originalVertices[dest][0] > xmin and ymax > self.originalVertices[dest][1] > ymin:
                    secondVal = destDict[dest]
                    topPaths.add(-secondVal, (src, dest))
        return topPaths.priorityValueResults


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
