import numpy as np

import Util
import Config

config = Config.BAD_GET_CONFIG()


class CalculateZooms:

    def __init__(self, points):
        self.tilesPerWindow = 3 # not mapnik's tile size, just used for managing crowding
        self.pointsPerCell = 1
        self.points = points
        self.numberedZoom= {}   # mapping from point ids to the zoom level at which they appear
        self.minX = min(float(p['x']) for p in self.points.values())
        self.maxX = max(float(p['x']) for p in self.points.values())
        self.minY = min(float(p['y']) for p in self.points.values())
        self.maxY = max(float(p['y']) for p in self.points.values())

        for p in self.points.values():
            p['popularity'] = float(p['popularity'])

    def simulateZoom(self):
        for z in range(config.MAX_ZOOM_SIMULATION):
            print(z, len(self.numberedZoom), len(self.points))
            if len(self.numberedZoom) == len(self.points):
                break
            self._simulateAZoomLevel(z)
        for id in self.points:
            if id not in self.numberedZoom:
                self.numberedZoom[id] = config.MAX_ZOOM_SIMULATION
        return self.numberedZoom

    def _simulateAZoomLevel(self, zoomLevel):

        idsByPopularity = [pair[0] for pair in Util.sort_by_feature(self.points, 'popularity')]
        
        topPerCluster = [[] for i in range(config.NUM_CLUSTERS)]
        n = self._numTopCountryPointsAtZoomLevel(zoomLevel)
        for id in idsByPopularity:
            c = int(self.points[id]['cluster'])
            if len(topPerCluster[c]) < n:
                topPerCluster[c].append(id)

        widthInTiles = (2 ** zoomLevel) * self.tilesPerWindow
        # print(widthInTiles)
        tileCounts = np.zeros((widthInTiles, widthInTiles), dtype=np.int)

        for clusterIds in topPerCluster:
            for id in clusterIds:
                (tileX, tileY) = self._getTileCoordinates(self.points[id], widthInTiles)
                if tileCounts[tileX, tileY] < self.pointsPerCell:
                    tileCounts[tileX, tileY] += 1
                    if id not in self.numberedZoom:
                        self.numberedZoom[id] = zoomLevel

        for id in idsByPopularity:
            (tileX, tileY) = self._getTileCoordinates(self.points[id], widthInTiles)
            if tileCounts[tileX, tileY] < self.pointsPerCell:
                tileCounts[tileX, tileY] += 1
                if id not in self.numberedZoom:
                    self.numberedZoom[id] = zoomLevel

        # print(tileCounts)
        #print(self.minX, self.maxX, self.minY, self.maxY, topPerCluster)
        return self.numberedZoom


    def _getTileCoordinates(self, point, widthInTiles):
        # Calculate normalized values between 0 and 1.0
        normalizedX = (float(point['x']) - self.minX) / (self.maxX - self.minX)
        normalizedY = (float(point['y']) - self.minY) / (self.maxY - self.minY)
        rawX = widthInTiles * normalizedX
        rawY = widthInTiles * normalizedY
        return (
            self._pinch(int(rawX), 0, widthInTiles - 1),
            self._pinch(int(rawY), 0, widthInTiles - 1)
        ) 


    def _numTopCountryPointsAtZoomLevel(self, zoomLevel):
        return zoomLevel ** 2


    def _pinch(self, z, minZ, maxZ):
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
    zoomDict = calc.simulateZoom()
    keys = list(zoomDict.keys())
    values = list(zoomDict.values())
    print keys