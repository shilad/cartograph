import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage
from geojson import Feature, FeatureCollection
from geojson import dumps, MultiPolygon
from scipy.ndimage.filters import gaussian_filter
import Config
config = Config.BAD_GET_CONFIG()


class ContourCreator:

    def __init__(self):
        pass

    def buildContours(self, coordinates):
        self.xs, self.ys = self._sortClusters(coordinates)
        self.CSs = self._calc_contour(self.xs, self.ys, 225)
        self.plyList = self._get_contours(self.CSs)

    @staticmethod
    def _sortClusters(xyCoords):
        x = [float(c['x']) for c in xyCoords]
        y = [float(c['y']) for c in xyCoords]
        clusters = [float(c['cluster']) for c in xyCoords]
        xs = [[] for i in range(config.NUM_CLUSTERS)]
        ys = [[] for i in range(config.NUM_CLUSTERS)]

        for i in range(len(clusters)):
            xs[int(clusters[i])].append(x[i])
            ys[int(clusters[i])].append(y[i])

        return xs, ys

    @staticmethod
    def _calc_contour(xs, ys, binSize):
        CSs = []
        for i in range(len(xs)):
            H, yedges, xedges = np.histogram2d(ys[i], xs[i],
                                           bins=binSize,
                                           range=[[np.min(xs[i]),
                                                  np.max(xs[i])],
                                                  [np.min(ys[i]),
                                                  np.max(ys[i])]])
            H = gaussian_filter(H, 2)
            extent = [xedges.min(), xedges.max(), yedges.min(), yedges.max()]

            smoothH = scipy.ndimage.zoom(H, 4)
            smoothH[smoothH < 0] = 0
            CSs.append(plt.contour(smoothH, extent=extent))

        return CSs

    @staticmethod
    def _get_contours(CSs):
        plyList = []
        for CS in CSs:
            plys = []
            for i in range(len(CS.collections)):
                shapes = []
                for j in range(len(CS.collections[i].get_paths())):
                    p = CS.collections[i].get_paths()[j]
                    v = p.vertices
                    shapes.append(v)
                plys.append(shapes)
            plyList.append(plys)
        return plyList

    @staticmethod
    def _gen_contour_polygons(plyList):
        countryGroup = []
        for plys in plyList:
            contourList = []
            for group in plys:
                contour = Contour(group)
                contour.createHoles()
                contourList.append(contour)
            countryGroup.append(contourList)

        featureAr = []
        for countryNum, contourList in enumerate(countryGroup):
            for index, contour in enumerate(contourList):
                geoPolys = []
                for polygon in contour.polygons:
                    geoPolys.append(polygon.points)
                newMultiPolygon = MultiPolygon(geoPolys)
                newFeature = Feature(geometry=newMultiPolygon, properties={"contourNum": index, "clusterNum": countryNum})
                featureAr.append(newFeature)
        return featureAr

    def makeContourFeatureCollection(self, outputfilename):
        featureAr = self._gen_contour_polygons(self.plyList)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(outputfilename, "w") as writeFile:
            writeFile.write(textDump)


class Contour:
    def __init__(self, shapes):
        self.shapes = shapes
        self.polygons = self._generatePolygons(self.shapes)

    @staticmethod
    def _generatePolygons(shapes):
        polys = set()
        for group in shapes:
            points = []
            for pt in group:
                points.append((pt[0], pt[1]))
            polys.add(Polygon(points))
        return polys

    def createHoles(self):
        toRemove = set()
        for poly in self.polygons:
            path = mplPath.Path(poly.points[0])
            for otherPolys in self.polygons:
                if poly is not otherPolys and path.contains_points(otherPolys.points[0]).all():
                    poly.children.add(otherPolys)
                    toRemove.add(otherPolys)
        for poly in toRemove:
            self.polygons.remove(poly)
        self.collapseHoles()

    def collapseHoles(self):
        for poly in self.polygons:
            poly.collapseChildren()


class Polygon:

    def __init__(self, points):
        self.points = [points]
        self.children = set()

    def collapseChildren(self):
        for child in self.children:
            self.points.append(child.points[0])
