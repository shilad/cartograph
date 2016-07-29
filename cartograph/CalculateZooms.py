import Config
import Utils
import luigi
import Coordinates
import Popularity
from Regions import MakeRegions
from collections import defaultdict
from LuigiUtils import MTimeMixin, TimestampedLocalTarget

# For information on the constants below see
# http://wiki.openstreetmap.org/wiki/Slippy_map_tilenames

# Scale denom for each zoom level

class CalculateZoomsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))



class ZoomLabeler(MTimeMixin, luigi.Task):
    '''
    Calculates a starting zoom level for every article point in the data,
    i.e. determines when each article label should appear.
    '''
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles",
                                                 "zoom_with_id"))

    def requires(self):
        return (MakeRegions(), 
                CalculateZoomsCode(),
                Coordinates.CreateFullCoordinates(),
                Popularity.PopularityIdentifier()
                )

    def run(self):
        config = Config.get()
        feats = Utils.read_features(config.get("GeneratedFiles",
                                              "popularity_with_id"),
                                    config.get("GeneratedFiles",
                                              "article_coordinates"),
                                    config.get("GeneratedFiles",
                                              "clusters_with_id"))
        
        counts = defaultdict(int)
        for row in feats.values():
            for k in row:
                counts[k] += 1
        print(counts)

        zoom = CalculateZooms(feats,
                              config.getint("MapConstants", "max_coordinate"),
                              config.getint("PreprocessingConstants", "num_clusters"))
        numberedZoomDict = zoom.simulateZoom(config.getint("MapConstants", "max_zoom"),
                                             config.getint("MapConstants", "first_zoom_label"))

        keys = list(numberedZoomDict.keys())
        zoomValue = list(numberedZoomDict.values())


        Utils.write_tsv(config.get("GeneratedFiles", "zoom_with_id"),
                        ("index", "maxZoom"), keys, zoomValue)


TOP_LEVEL_COORDINATES = (360, 170.1022)


class QuadTree:
    def __init__(self, depth, leftX, topY, size,
                 capacity, maxDepth, isTopLevel=True):
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
        '''
        Inserts a point into the quadrant if the capacity of
        points per tile has not been reached. Adds the children 
        of the tile into the quadtree structure and adds the 
        point to the child tile if it contains the point. 
        '''
        c = self.capacity

        if self.isTopLevel is True:
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
            self.children.append(QuadTree(d, self.leftX + s,
                                          self.topY, s, c, md))
            self.children.append(QuadTree(d, self.leftX,
                                          self.topY + s, s, c, md))
            self.children.append(QuadTree(d, self.leftX + s,
                                          self.topY + s, s, c, md))

        for c in self.children:
            if c.contains(x, y):
                c.insert(x, y, pid)
                break
        else:
            assert(False, '%s doesnt contain %s, %s' % (self, x, y))

    def contains(self, x, y):
        '''
        Determines if a point exists in a tile. 
        '''
        return (x >= self.leftX and x <= self.leftX + self.size
                and y >= self.topY and y <= self.topY + self.size)

    def __repr__(self):
        return ('qt for (%.4f %.4f %.4f %.4f)'
                % (self.leftX, self.topY, self.leftX + self.size,
                   self.topY + self.size))


class CalculateZooms:

    def __init__(self, points, maxCoordinate, numClusters):
        self.pointsPerTile = 35
        self.maxCoordinate = maxCoordinate
        self.points = { k : v for (k, v) in points.items() if 'x' in v and 'y' in v }
        assert(len(points) > 0)
        # mapping from point ids to the zoom level at which they appear
        self.numberedZoom = {}
        self.minX = min(float(p['x']) for p in self.points.values())
        self.maxX = max(float(p['x']) for p in self.points.values())
        self.minY = min(float(p['y']) for p in self.points.values())
        self.maxY = max(float(p['y']) for p in self.points.values())
        self.numClusters = numClusters

        for p in self.points.values():
            p['popularity'] = float(p['popularity'])

    def simulateZoom(self, maxZoom, firstZoomLevel):
        '''
        Simulates zooming of the map using a quadtree. Additional points
        are added if capacity of tile is not full. Runs a DFS on the 
        quadtree to return the max zoom level for every article. 
        '''

        # Order ids by overall popualarity
        idsByPopularity = [pair[0] for pair in Utils.sort_by_feature(self.points, 'popularity')]

        # Get top points per cluster
        nClusters = self.numClusters
        topPerCluster = [[] for i in range(nClusters)]
        for id in idsByPopularity:
            c = int(self.points[id]['cluster'])
            topPerCluster[c].append(id)

        added = set()

        nAdded = [0]
        mc = 1.0 * self.maxCoordinate
        qt = QuadTree(firstZoomLevel, -mc, -mc, mc * 2,
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
                print 'Simulation added %d of %d points' % (nAdded[0], len(self.points))

            iterN += 1

        # Run a DFS on the tree
        counts = [0] * 50

        def dfs(node):
            for p in node.points:
                self.numberedZoom[p] = node.depth
                counts[node.depth] += 1
            for child in node.children:
                dfs(child)

        dfs(qt)

        return self.numberedZoom
