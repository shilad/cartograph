import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage
from geojson import Feature, FeatureCollection
from geojson import dumps, Polygon
import copy
import Util


class Contours:

    def __init__(self, dataName, fileName):
        self.file = fileName
        self.data = dataName

    def _calc_contour(self, csvFile, binSize):
        xyCoords = Util.read_tsv(csvFile)
        x = map(float, xyCoords["x"])
        y = map(float, xyCoords["y"])
        contBuffer = 20

        H, yedges, xedges = np.histogram2d(y, x,
                                           bins=binSize,
                                           range=[[np.min(x) - contBuffer,
                                                  np.max(x) + contBuffer],
                                                  [np.min(y) - contBuffer,
                                                  np.max(y) + contBuffer]])
        extent = [xedges.min(), xedges.max(), yedges.min(), yedges.max()]

        smoothH = scipy.ndimage.zoom(H, 4)
        smoothH[smoothH < 0] = 0

        return (plt.contour(smoothH, extent=extent))

    def _remove_array(self, L, arr):
            ind = 0
            size = len(L)
            while ind != size and not np.array_equal(L[ind], arr):
                ind += 1
            if ind != size:
                L.pop(ind)
            else:
                raise ValueError('array not found in list.')

    def _get_contours(self):
        CS = self._calc_contour(self.data, 35)
        plys = []
        for i in range(len(CS.collections)):
            shapes = []
            for j in range(len(CS.collections[i].get_paths())):
                p = CS.collections[i].get_paths()[j]
                v = p.vertices
                shapes.append(v)
            plys.append(shapes)
        return plys

    def _sort_contours(self):
        plys = self._get_contours()
        copy_lst = copy.deepcopy(plys)
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

        for shape in polyGroups:
            newPolygon = Polygon(shape)
            newFeature = Feature(geometry=newPolygon)
            featureAr.append(newFeature)

        return featureAr

    def makeContourFeatureCollection(self):
        featureAr = self._gen_contour_features()
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(self.file, "w") as writeFile:
            writeFile.write(textDump)
