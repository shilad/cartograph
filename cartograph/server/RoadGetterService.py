import os
from math import log
import falcon
import jinja2
import heapq
import json

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
    def __init__(self, semanticPathFile, origVertsPath, pathToZPop, pathToBundledVertices, pathtoBundleEdges):
        #This sets up all the variables we need for any work done.
        self.articlesZpop = {}
        with open(pathToZPop, "r") as zpop:
            for line in zpop:
                lst = line.split()
                self.articlesZpop[lst[0]] = lst[1]
        self.originalVertices = {}
        with open(origVertsPath) as ptov:
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
        with open(pathtoBundleEdges, 'r') as ptbe:
            for line in ptbe:
                lst = line.split()
                self.bundledEdges[(lst[0], lst[1])] = lst[2]
        self.edgeDictionary, self.outboundPaths = self.getEdgeDictionaries(semanticPathFile)

    def on_get(self, req, resp):
        #print("hehe ecks dee")
        paths, pointsInPort = self.getPathsInViewPort(float(req.params['xmin']), float(req.params['xmax']),
                                                      float(req.params['ymin']), float(req.params['ymax']), int(req.params['n_cities']))
        #print(req.params['xmin'], req.params['xmax'], req.params['ymin'], req.params['ymax'])
        output = self.formWeightedJSONPaths(paths)
        resp.status = falcon.HTTP_200
        resp.content_type = "application/json"  #getMimeType(file)
        resp.body = json.dumps(output)


    def formWeightedJSONPaths(self, paths):
        jsonPaths = {}
        print(paths)
        for path in paths:
            coordList = []
            print('path', path)
            if len(path) == 0: continue
            for i in range(0, len(path)-1):
                src = path[i]
                dest = path[i+1]
                entry = []
                if src in self.originalVertices:
                    entry.append(self.originalVertices[src])
                else:
                    entry.append(self.bundledVertices[src])
                if dest in self.originalVertices:
                    entry.append(self.originalVertices[dest])
                else:
                    entry.append(self.bundledVertices[dest])
                if (src, dest) in self.bundledEdges:
                    weight = float(self.bundledEdges[(src, dest)])
                else:
                    weight = 1
                entry.append([weight])
                coordList.append(entry)
                #print(coordList)
            if path[0] in jsonPaths:
                jsonPaths[path[0]].append(coordList)
            else:
                jsonPaths[path[0]] = [coordList]
        return jsonPaths

    def getPath(self, childEdgeId, edgeDict, frontStack=[], backStack=[]):
        if(edgeDict[childEdgeId][0] != edgeDict[childEdgeId][1]):
            frontStack.append(edgeDict[childEdgeId][0])
            backStack.insert(0, edgeDict[childEdgeId][1])

        if (len(edgeDict[childEdgeId]) == 4):
            # we still have parents!
            parentID = edgeDict[childEdgeId][2]
            return self.getPath(parentID, edgeDict, frontStack, backStack)
        elif (len(edgeDict[childEdgeId]) == 3):
            frontStack = frontStack + backStack
            return frontStack

    def getEdgeDictionaries(self, semanticPath):
        outboundPaths = {}
        edgeDictionary = {}
        with open(semanticPath, 'r') as dictFormingSemanticTree:
            for line in dictFormingSemanticTree:
                elements = line.split(" ")
                edgeDictionary[elements[0]] = elements[1:]  # Edge ID as key,  [src, dest, parent, weight] as vals
                # if both src and dst are in orig Vertices:
                if (elements[1] in self.originalVertices and elements[2] in self.originalVertices):  # elements = [edgeId, src, dst, parent, weight]
                    if len(elements) == 4:  # here there's EdgeID, src, dest, weight, here we ARE at the parent
                        if elements[1] in outboundPaths:
                            outboundPaths[elements[1]].update({elements[2]: [elements[0], elements[3]]})
                        else:
                            outboundPaths[elements[1]] = {elements[2]: [elements[0], elements[3]]}
                    elif len(elements) == 5:  # here we are still at a child and have to append the parent. format: Src key -> dest Key -> [EdgeId, Weight, Parent if exists], if path[src][dest].size = 3, we gotta keep going, if =2, we at end
                        if elements[1] in outboundPaths:
                            outboundPaths[elements[1]].update({elements[2]: [elements[0], elements[4], elements[3]]})
                        else:
                            outboundPaths[elements[1]] = {elements[2]: [elements[0], elements[4], elements[3]]}
        return edgeDictionary, outboundPaths

    def getPathsInViewPort(self, xmin, xmax, ymin, ymax, n_cities=5):
        pointsinPort = []

        for point in self.originalVertices:
            if xmax > float(self.originalVertices[point][0]) > xmin and ymin < float(self.originalVertices[point][1]) < ymax:
                pointsinPort.append(point)  # points in port is an array of pointIDs which are strings.
        cities = self.get_n_most_prominent_cities(n_cities, pointsinPort)
        paths = self.getPathsForEachCity(cities)
        return paths, pointsinPort

    def get_n_most_prominent_cities(self, n, vertices_in_view_port):
        n_cities = PrioritySet(max_size=n)
        for vertex in vertices_in_view_port:
            z_pop_score = self.articlesZpop[vertex]
            n_cities.add(-float(z_pop_score), vertex)
        return n_cities.heap

    def edgeShouldShow(self,  src, dest, threshold = 2):
        '''
        If sum of the zpop score of the two articles is greater than a threshold the edge should not show
        :param src:
        :param dest:
        :param threshold:
        :return:
        '''
        srcZpop = float(self.articlesZpop[src])
        destZpop = float(self.articlesZpop[dest])

        if srcZpop + destZpop > threshold:
            return False
        else:
            return True

    def getPathsForEachCity(self, citiesToShowEdges):
        pathsToMine = []
        thresholdVal = 3
        for city in citiesToShowEdges:
            if city[1] in self.outboundPaths:
                for dest in self.outboundPaths[city[1]]:
                    if self.edgeShouldShow(city[1], dest, threshold= thresholdVal):
                        pathsToMine.append(
                            (city[1], dest))  # outpaths and inpaths include points and dest of edges we want to reconstruct
        paths = []
        print("Finding paths now. Paths to do: " + str(len(pathsToMine)))
        for path in pathsToMine:
            results = self.getPath(self.outboundPaths[path[0]][path[1]][0], self.edgeDictionary, [], [])
            paths.append(results)

            if len(paths) % 100000 == 0:
                print(len(paths))
        return paths