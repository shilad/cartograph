import numpy as np

import Util
import Config

config = Config.BAD_GET_CONFIG()


# For information on the constants below see 
# http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames

# Scale denom for each zoom level
ZOOM_LEVEL_SCALE_DENOMS = [ 559082264 ]
for i in range(config.MAX_ZOOM):
    ZOOM_LEVEL_SCALE_DENOMS.append(ZOOM_LEVEL_SCALE_DENOMS[-1] / 2)

# Proportion of map per tile.
ZOOM_LEVEL_DEGREES_PER_TILE = [ (360, 170.1022) ]
for i in range(config.MAX_ZOOM):
    prev = ZOOM_LEVEL_DEGREES_PER_TILE[-1]
    ZOOM_LEVEL_DEGREES_PER_TILE.append((prev[0] / 2, prev[1] / 2))

# Proportion of map per zoom level.
ZOOM_MAP_PROP_PER_TILE = []
for i in range(config.MAX_ZOOM + 1):
    frac = ZOOM_LEVEL_DEGREES_PER_TILE[i][1] / (config.MAX_COORDINATE * 2)
    ZOOM_MAP_PROP_PER_TILE.append(frac)

# Minimum zoom level that encompasses a whole map on a tile.
MIN_FULL_MAP_ZOOM = max( z for z in range(config.MAX_ZOOM)
                         if ZOOM_MAP_PROP_PER_TILE[z] >= 1.0 )

class QuadTree:
    def __init__(self, depth, leftX, topY, size, capacity, maxDepth):
        self.depth = depth
        self.children = []
        self.points = []
        self.leftX = leftX
        self.topY = topY
        self.size = size
        self.capacity = capacity
        self.maxDepth = maxDepth

    def insert(self, x, y, pid):
        if self.depth >= self.maxDepth or len(self.points) < self.capacity:
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

    def __init__(self, points):
        self.pointsPerTile = 2
        self.points = points
        self.numberedZoom= {}   # mapping from point ids to the zoom level at which they appear
        self.minX = min(float(p['x']) for p in self.points.values())
        self.maxX = max(float(p['x']) for p in self.points.values())
        self.minY = min(float(p['y']) for p in self.points.values())
        self.maxY = max(float(p['y']) for p in self.points.values())

        for p in self.points.values():
            p['popularity'] = float(p['popularity'])

    def simulateZoom(self):

        # Order ids by overall popualarity
        idsByPopularity = [pair[0] for pair in Util.sort_by_feature(self.points, 'popularity')]

        # Get top points per cluster 
        nClusters = config.NUM_CLUSTERS
        topPerCluster = [[] for i in range(nClusters)]
        for id in idsByPopularity:
            c = int(self.points[id]['cluster'])
            topPerCluster[c].append(id)

        added = set()

        nAdded = [ 0 ]
        mc = 1.0 * config.MAX_COORDINATE
        qt = QuadTree(MIN_FULL_MAP_ZOOM, -mc, -mc, mc * 2, self.pointsPerTile, config.MAX_ZOOM)

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

            if iterN % 100 == 0: 
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
