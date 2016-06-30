import numpy as np

import Util
import Config

config = Config.BAD_GET_CONFIG()


class CalculateZooms:

    def __init__(self, points):
        self.tilesPerWindow = 3 # not mapnik's tile size, just used for managing crowding
        self.pointsPerCell = 3
        self.points = points
        self.maxZoom = {}   # mapping from point ids to the zoom level at which they appear
        self.minX = min(float(p['x']) for p in self.points.values())
        self.maxX = max(float(p['x']) for p in self.points.values())
        self.minY = min(float(p['y']) for p in self.points.values())
        self.maxY = max(float(p['y']) for p in self.points.values())

        for p in self.points.values():
            p['popularity'] = float(p['popularity'])

    def simulate(self):
        for z in range(20):
            print(z, len(self.maxZoom), len(self.points))
            if len(self.maxZoom) == len(self.points):
                break
            self.simulateZoom(z)

    def simulateZoom(self, zoomLevel):

        idsByPopularity = [pair[0] for pair in Util.sort_by_feature(self.points, 'popularity')]
        
        topPerCluster = [[] for i in range(config.NUM_CLUSTERS)]
        n = self.numTopCountryPointsAtZoomLevel(zoomLevel)
        for id in idsByPopularity:
            c = int(self.points[id]['cluster'])
            if len(topPerCluster[c]) < n:
                topPerCluster[c].append(id)

        widthInTiles = (2 ** zoomLevel) * self.tilesPerWindow
        print(widthInTiles)
        tileCounts = np.zeros((widthInTiles, widthInTiles), dtype=np.int)

        for clusterIds in topPerCluster:
            for id in clusterIds:
                (tileX, tileY) = self.getTileCoordinates(self.points[id], widthInTiles)
                if tileCounts[tileX, tileY] < self.pointsPerCell:
                    tileCounts[tileX, tileY] += 1
                    if id not in self.maxZoom:
                        self.maxZoom[id] = zoomLevel

        for id in idsByPopularity:
            (tileX, tileY) = self.getTileCoordinates(self.points[id], widthInTiles)
            if tileCounts[tileX, tileY] < self.pointsPerCell:
                tileCounts[tileX, tileY] += 1
                if id not in self.maxZoom:
                    self.maxZoom[id] = zoomLevel

        print(tileCounts)
        #print(self.minX, self.maxX, self.minY, self.maxY, topPerCluster)


    def getTileCoordinates(self, point, widthInTiles):
        # Calculate normalized values between 0 and 1.0
        normalizedX = (float(point['x']) - self.minX) / (self.maxX - self.minX)
        normalizedY = (float(point['y']) - self.minY) / (self.maxY - self.minY)
        rawX = widthInTiles * normalizedX
        rawY = widthInTiles * normalizedY
        return (
            pinch(int(rawX), 0, widthInTiles - 1),
            pinch(int(rawY), 0, widthInTiles - 1)
        ) 


    def numTopCountryPointsAtZoomLevel(self, zoomLevel):
        return zoomLevel ** 2


def pinch(z, minZ, maxZ):
    if z > maxZ:
        return maxZ
    elif z < minZ:
        return minZ
    else:
        return z

if __name__ == '__main__':
    feats = Util.read_features(config.FILE_NAME_NUMBERED_POPULARITY,
                        config.FILE_NAME_ARTICLE_COORDINATES,
                        config.FILE_NAME_NUMBERED_CLUSTERS)
    calc = CalculateZooms(feats)
    calc.simulate()