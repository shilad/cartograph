import os

import falcon
import jinja2
import heapq
import json

from cartograph.server.ConfigService import ConfigService
from cartograph.server.ServerUtils import getMimeType
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
    def __init__(self, config, semanticPathFile, origVertsPath, pathToZPop, pathToBundledVertices, pathToBundledEdges):
        #This sets up all the variables we need for any work done.
        pathToOriginalVertices = origVertsPath
        semanticPath = semanticPathFile
        self.config = config
        self.configService = ConfigService(config)
        self.outboundPaths = {}
        self.edgeDictionary = {}
        self.inboundPaths = {}
        self.articlesZpop = {}
        with open(pathToZPop, "r") as zpop:
            for line in zpop:
                lst = line.split()
                self.articlesZpop[lst[0]] = lst[1]
        self.originalVertices = {}
        with open(pathToOriginalVertices) as ptov:
            for line in ptov:
                lst = line.split()
                if len(lst) == 1: continue
                self.originalVertices[lst[0]] = lst[1:]
        self.bundledVertices = {}
        with open(pathToBundledVertices, 'r') as ptbv:
            for line in ptbv:
                lst = line.split()
                self.bundledVertices[lst[0]] = lst[1:]
        self.bundledEdges = {}
        with open(pathToBundledEdges) as pte:
            for line in pte:
                lst = line.split()
                self.bundledEdges[(lst[0], lst[1])] = lst[2]
        self.edgeDictionary, self.inboundPaths, self.outboundPaths = self.getEdgeDictionaries(semanticPath)

    def on_get(self, req, resp):
        paths, pointsInPort = self.getPathsInViewPort(req.params['xmin'], req.params['xmax'], req.params['ymin'], req.params['ymax'], req.params['n_cities'])
        resp.status = falcon.HTTP_200
        resp.content_type = getMimeType(file)


    def getEdgeDictionaries(self, semanticPath):
        outboundPaths = {}
        edgeDictionary = {}
        inboundPaths = {}
        with open(semanticPath, 'r') as dictFormingSemanticTree:
            for line in dictFormingSemanticTree:
                elements = line.split(" ")
                edgeDictionary[elements[0]] = elements[1:]  # Edge ID as key,  [src, dest, parent, weight] as vals
                # if both src and dst are in orig Vertices:
                if (elements[1] in self.originalVertices and elements[
                    2] in self.originalVertices):  # elements = [edgeId, src, dst, parent, weight]
                    #       pairings.append((elements[1], elements[2]))
                    if len(elements) == 4:  # here there's EdgeID, src, dest, weight, here we ARE at the parent
                        if elements[1] in outboundPaths:
                            outboundPaths[elements[1]].update({elements[2]: [elements[0], elements[3]]})
                        else:
                            outboundPaths[elements[1]] = {elements[2]: [elements[0], elements[3]]}
                        if elements[2] in inboundPaths:
                            inboundPaths[elements[2]].update({elements[1]: [elements[0], elements[3]]})
                        else:
                            inboundPaths[elements[2]] = {elements[1]: [elements[0], elements[3]]}
                    elif len(
                            elements) == 5:  # here we are still at a child and have to append the parent. format: Src key -> dest Key -> [EdgeId, Weight, Parent if exists], if path[src][dest].size = 3, we gotta keep going, if =2, we at end
                        if elements[1] in outboundPaths:
                            outboundPaths[elements[1]].update({elements[2]: [elements[0], elements[4], elements[3]]})
                        else:
                            outboundPaths[elements[1]] = {elements[2]: [elements[0], elements[4], elements[3]]}
                        if elements[2] in inboundPaths:
                            inboundPaths[elements[2]].update({elements[1]: [elements[0], elements[4], elements[3]]})
                        else:
                            inboundPaths[elements[2]] = {elements[1]: [elements[0], elements[4], elements[3]]}
        return edgeDictionary, inboundPaths, outboundPaths

    def getPathsInViewPort(self, xmin, xmax, ymin, ymax, n_cities = 10):
        pointsinPort = []

        for point in self.originalVertices:
            if xmax > float(self.originalVertices[point][0]) > xmin and ymin < float(self.originalVertices[point][1]) < ymax:
                pointsinPort.append(point)  # points in port is an array of pointIDs which are strings.
        cities = self.get_n_most_prominent_cities(n_cities, pointsinPort)
        paths = self.getPathsForEachCity(cities, xmin, xmax, ymin, ymax )
        return paths, pointsinPort
    def get_n_most_prominent_cities(self, n, vertices_in_view_port):
        n_cities = PrioritySet(max_size=n)

        for vertex in vertices_in_view_port:
            z_pop_score = self.articlesZpop[vertex]
            n_cities.add(-float(z_pop_score), vertex)


        return n_cities.heap
    def getPathsForEachCity(self, citiesToShowEdges, xmin, xmax, ymin, ymax,):
        outpathsToMine = []
        inpathsToMine = []
        threshholdval = 4
        for city in citiesToShowEdges:

            if city[1] in self.outboundPaths:
                for dest in self.outboundPaths[city[1]]:
                    if self.edgeShouldShow(city[1], dest, threshold= threshholdval):
                        outpathsToMine.append(
                            (city[1], dest))  # outpaths and inpaths include points and dest of edges we want to reconstruct

            #if city[1] in self.inboundPaths:
                #for src in self.inboundPaths[city[1]]:

                    #p = self.originalVertices[src]
                    #if (xmax < float(p[0]) or float(p[0]) < xmin) or (ymin > float(p[1]) or float(p[1]) > ymax):
                      # pass
                        #if self.edgeShouldShow(src, city[1], threshold= threshholdval):
                            #inpathsToMine.append([src, city[1]])

        paths = []

        print("Finding paths now. Paths to do: " + str(len(inpathsToMine) + len(outpathsToMine)))
        for path in inpathsToMine:  # path[0] = src, path[1] = dest
            results = self.getPath(self.inboundPaths[path[1]][path[0]][0], self.edgeDictionary, [], [])
            paths.append(results)

            if (len(paths) % 100000 == 0):
                print(len(paths))

        for path in outpathsToMine:
            results = self.getPath(self.outboundPaths[path[0]][path[1]][0], self.edgeDictionary, [], [])
            paths.append(results)

            if len(paths) % 100000 == 0:
                print(len(paths))
        return paths