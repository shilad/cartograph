import Util
# For information on the constants below see 
# http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames

# Scale denom for each zoom level

TOP_LEVEL_COORDINATES = (360, 170.1022)

class QuadTree:
    def __init__(self, depth, leftX, topY, size, capacity, maxDepth, isTopLevel=True):
        self.isTopLevel = isTopLevel
        self.capacityAtTop = 45
        self.depth = depth
        self.children = []
        self.points = []
        self.leftX = leftX
        self.topY = topY
        self.size = size
        self.capacity = capacity
        self.maxDepth = maxDepth

    def insert(self, x, y, pid):
        c = self.capacity

        if self.isTopLevel == True:
            c = self.capacityAtTop

        if self.depth >= self.maxDepth or len(self.points) < c:
            self.points.append(pid)
            return

        if not self.children:
            d = self.depth + 1
            s = self.size / 2
            c = self.capacity
            md = self.maxDepth
            self.children.append(QuadTree(d, self.leftX, self.topY, s, c, md))
            self.children.append(QuadTree(d, self.leftX + s, self.topY, s, c, md))
            self.children.append(QuadTree(d, self.leftX, self.topY + s, s, c, md))
            self.children.append(QuadTree(d, self.leftX + s, self.topY + s, s, c, md))

        for c in self.children:
            #print('checking %s for %f, %f' % (c, x, y))
            if c.contains(x, y):
                c.insert(x, y, pid)
                break
        else:
            assert(False)

    def contains(self, x, y):
        return (x >= self.leftX and x <= self.leftX + self.size
            and y >= self.topY  and y <= self.topY + self.size)

    def __repr__(self):
        return ('qt for (%.4f %.4f %.4f %.4f)'
            % (self.leftX, self.topY, self.leftX + self.size, self.topY + self.size))

class CalculateZooms:

    def __init__(self, points, maxCoordinate, numClusters):
        self.pointsPerTile = 35
        self.maxCoordinate = maxCoordinate
        self.points = points
        self.numberedZoom= {}   # mapping from point ids to the zoom level at which they appear
        self.minX = min(float(p['x']) for p in self.points.values())
        self.maxX = max(float(p['x']) for p in self.points.values())
        self.minY = min(float(p['y']) for p in self.points.values())
        self.maxY = max(float(p['y']) for p in self.points.values())
        self.numClusters = numClusters

        for p in self.points.values():
            p['popularity'] = float(p['popularity'])

    def simulateZoom(self, maxZoom, firstZoomLevel):

        # Order ids by overall popualarity
        idsByPopularity = [pair[0] for pair in Util.sort_by_feature(self.points, 'popularity')]

        # Get top points per cluster 
        nClusters = self.numClusters
        topPerCluster = [[] for i in range(nClusters)]
        for id in idsByPopularity:
            c = int(self.points[id]['cluster'])
            topPerCluster[c].append(id)

        coordRange = min(TOP_LEVEL_COORDINATES)
        lastZoom = firstZoomLevel
        # for i in range(18):
        #     if coordRange >= self.maxCoordinate:
        #         lastZoom = i
        #     coordRange /= 2.0
        added = set()

        nAdded = [0]
        mc = 1.0 * self.maxCoordinate
        qt = QuadTree(lastZoom, -mc, -mc, mc * 2,
                      self.pointsPerTile, maxZoom)

        def maybeAddPoint(pid):
            if pid in added: return
            x = float(self.points[pid]['x'])
            y = float(self.points[pid]['y'])
            qt.insert(x, y, pid)
            added.add(pid)
            nAdded[0] += 1

        iterN = 0
        while len(added) != len(self.points): 
            for i in range(iterN * nClusters, (iterN + 1) * nClusters):
                if i < len(idsByPopularity):
                    maybeAddPoint(idsByPopularity[i])

            for i in range(nClusters):
                if iterN < len(topPerCluster[i]):
                    maybeAddPoint(topPerCluster[i][iterN])

            if iterN % 10000 == 0: 
                print('Simulation added %d of %d points' % (nAdded[0], len(self.points)))

            iterN += 1
            
        # Run a DFS on the tree
        counts = [ 0 ] * 50
        def dfs(node):
            for p in node.points:
                self.numberedZoom[p] = node.depth
                counts[node.depth] += 1
            for child in node.children:
                dfs(child)
            
        dfs(qt) 

        return self.numberedZoom

if __name__ == '__main__':
    feats = Util.read_features(config.FILE_NAME_NUMBERED_POPULARITY,
                        config.FILE_NAME_ARTICLE_COORDINATES,
                        config.FILE_NAME_NUMBERED_CLUSTERS)
    calc = CalculateZooms(feats)
    zoomDict = calc.simulateZoom()
    keys = list(zoomDict.keys())
    values = list(zoomDict.values())
    #print keys
