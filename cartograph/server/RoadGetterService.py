import falcon
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
    def __init__(self, origEdgesPath, origVertsPath, pathToZPop, pathToNames):
        #This sets up all the variables we need for any work done.
        self.articlesZpop = {} #here articlesZpop key is article ID, and val is a float zpop val
        with open(pathToZPop, "r") as zpop:
            for line in zpop:
                lst = line.split()
                if lst[0] == "index":
                    continue
                if lst[0] == "3019":
                    self.articlesZpop[lst[0]] = 12
                    continue
                self.articlesZpop[lst[0]] = float(lst[1]) + 1.0
        self.names = {}
        with open(pathToNames, "r") as namesFile:
            for line in namesFile:
                lst = line.split('\t')
                if lst[0] == "id": continue
                self.names[lst[0]] = lst[1]
        self.originalVertices = {}
        with open(origVertsPath) as ptov:
            for line in ptov:
                lst = line.split()
                if len(lst) == 1: continue
                self.originalVertices[lst[0]] = [float(lst[1]), float(lst[2])]
        self.origEdges = {}
        self.edgeIDPath = {}
        edgeGenerator = 1
        with open(origEdgesPath, 'r') as ptbe:
            for line in ptbe:
                lst = line.split()
                if len(lst) == 1: continue
                if lst[0] in self.origEdges:
                    self.origEdges[lst[0]].append([lst[1], edgeGenerator])
                else:
                    self.origEdges[lst[0]] = [[lst[1], edgeGenerator]]
                self.edgeIDPath[edgeGenerator] = lst
                edgeGenerator+=1

    def on_get(self, req, resp):
        #print("hehe ecks dee")
        edges = self.getPathsInViewPort(float(req.params['xmin']), float(req.params['xmax']),
                                        float(req.params['ymin']), float(req.params['ymax']),
                                        int(req.params['num_paths']))
        pathIds = []
        for edge in edges:
            if len(edge) == 2:
                pathIds.append(edge[1])
        paths = []
        pathsCovered = []
        bothWays = []
        for pathId in pathIds:
            [src, dest] = self.edgeIDPath[pathId]
            pathsCovered.append([src, dest])
            if ([dest, src] in pathsCovered):

                bothWays.append((src,dest))

                continue
            srcCord = self.originalVertices[src]  # both of the Cord vals are arrays [y,x]
            dstCord = self.originalVertices[dest]
            srcCord = [srcCord[1], srcCord[0]]
            dstCord = [dstCord[1], dstCord[0]]
            paths.append([src, self.names[src][:-1], srcCord])
            paths.append([dest, self.names[dest][:-1], dstCord])
        jsonDict  = {"paths":  paths, "bothWays": bothWays}
        resp.status = falcon.HTTP_200
        resp.content_type = "application/json"  #getMimeType(file)
        #print(json.dumps(jsonDict))
        #print("len", len(json.dumps(jsonDict)))
        resp.body = json.dumps(jsonDict)




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

    def getPathsInViewPort(self, xmin, xmax, ymin, ymax, num_paths):
        pointsinPort = []
        for point in self.originalVertices:
            if xmax > float(self.originalVertices[point][0]) > xmin and ymin < float(self.originalVertices[point][1]) < ymax:
                pointsinPort.append(point)  # points in port is an array of pointIDs which are strings.
        topPaths = PrioritySet(max_size=num_paths)

        for point in pointsinPort:
            if point in self.origEdges:
                for pair in self.origEdges[point]:
                    dest = pair[0]
                    edgeID = pair[1]
                    if dest in self.originalVertices and xmax > float(self.originalVertices[dest][0]) > xmin and ymin < float(self.originalVertices[dest][1]) < ymax:
                        if dest in self.articlesZpop and edgeID in self.edgeIDPath:
                            edgeVal = self.articlesZpop[point]*self.articlesZpop[dest]
                            topPaths.add(-edgeVal, edgeID)
        return topPaths.heap

