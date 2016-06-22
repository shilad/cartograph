import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage
from geojson import Feature, FeatureCollection
from geojson import dumps, Polygon
import copy
import Util

from scipy.ndimage.filters import gaussian_filter


class ContourCreater:

    def __init__(self, dataName, fileName):
        self.file = fileName
        self.data = dataName
        self.CS = self._calc_contour(self.data, 225)
        self.plys = self._get_contours()

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

    def _get_contours(self):
        plys = []
        for i in range(len(self.CS.collections)):
            shapes = []
            for j in range(len(self.CS.collections[i].get_paths())):
                p = self.CS.collections[i].get_paths()[j]
                v = p.vertices
                shapes.append(v)
            plys.append(shapes)
        return plys

    def _remove_array(self, L, arr):
            ind = 0
            size = len(L)
            while ind != size and not np.array_equal(L[ind], arr):
                ind += 1
            if ind != size:
                L.pop(ind)
            else:
                raise ValueError('array not found in list.')

    def _sort_contours(self):
        plys = self._get_contours()
        copy_lst = copy.deepcopy(self.plys)
        count = 0
        for contours in copy_lst:
            newShape = []
            for shapes in contours:
                bbPath = mplPath.Path(shapes)
                for intShapes in contours:
                    if (shapes[0][0] != intShapes[0][0]) \
                       and (shapes[0][1] != intShapes[0][1]) \
                       and bbPath.contains_point((intShapes[0][0], intShapes[0][1])):
                        if len(newShape) == 0:
                            newShape.append(shapes)
                            self._remove_array(plys[count], shapes)
                        newShape.append(intShapes)
                        self._remove_array(plys[count], intShapes)
            if len(newShape) != 0:
                plys.append(newShape)
            count += 1
        return plys

    def _gen_contour_features(self):
        featureAr = []
        polyGroups = []
        for group in self._sort_contours():
            polys = []
            for shape in group:
                polyPoints = []
                for pt in shape:
                    polyPoints.append((pt[0], pt[1]))
                polys.append(polyPoints)
            polyGroups.append(polys)

        for index, shape in enumerate(polyGroups):
            newPolygon = Polygon(shape)
            newFeature = Feature(geometry=newPolygon, properties={"clusterNum": index})
            featureAr.append(newFeature)

        return featureAr

    def makeContourFeatureCollection(self):
        featureAr = self._gen_contour_features()
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(self.file, "w") as writeFile:
            writeFile.write(textDump)

    class Contour():

        def __init__(self):
            pass
