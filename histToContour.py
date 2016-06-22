import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage
from geojson import Feature, FeatureCollection
from geojson import dumps, Polygon, MultiPolygon
import copy
import Util

from scipy.ndimage.filters import gaussian_filter


class ContourCreator:

    def __init__(self, dataName, fileName):
        self.file = fileName
        self.data = dataName
        self.CS = self._calc_contour(self.data, 225)
        self.plys = self._get_contours(self.CS)

    @staticmethod
    def _calc_contour(tsvFile, binSize):
        xyCoords = Util.read_tsv(tsvFile)
        x = map(float, xyCoords["x"])
        y = map(float, xyCoords["y"])

        H, yedges, xedges = np.histogram2d(y, x,
                                           bins=binSize,
                                           range=[[np.min(x),
                                                  np.max(x)],
                                                  [np.min(y),
                                                  np.max(y)]])
        H = gaussian_filter(H, 2)
        extent = [xedges.min(), xedges.max(), yedges.min(), yedges.max()]

        smoothH = scipy.ndimage.zoom(H, 4)
        smoothH[smoothH < 0] = 0

        return (plt.contour(smoothH, extent=extent))

    @staticmethod
    def _get_contours(CS):
        plys = []
        for i in range(len(CS.collections)):
            shapes = []
            for j in range(len(CS.collections[i].get_paths())):
                p = CS.collections[i].get_paths()[j]
                v = p.vertices
                shapes.append(v)
            plys.append(shapes)
        return plys

    @staticmethod
    def _gen_contour_polygons(plys):
        contourList = []
        for group in plys:
            contour = ContourCreator.Contour(group)
            contour.createHoles()
            contourList.append(contour)

        featureAr = []
        for index, contour in enumerate(contourList):
            geoPolys = []
            for polygon in contour.polygons:
                geoPolys.append(polygon.points)
            newMultiPolygon = MultiPolygon(geoPolys)
            newFeature = Feature(geometry=newMultiPolygon, properties={"contourNum": index})
            featureAr.append(newFeature)
        return featureAr

    def makeContourFeatureCollection(self):
        featureAr = self._gen_contour_polygons(self.plys)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(self.file, "w") as writeFile:
            writeFile.write(textDump)

    class Contour():

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
                polys.add(ContourCreator.Polygon(points))
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

    class Polygon():

        def __init__(self, points):
            self.points = [points]
            self.children = set()

        def collapseChildren(self):
            for child in self.children:
                self.points.append(child.points[0])
