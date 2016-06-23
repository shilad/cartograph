import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage
from geojson import Feature, FeatureCollection
from geojson import dumps, Polygon
import copy
from src import Util


class Contours:

    def __init__(self):
        pass

    def _calc_contour(self, articleCoords, binSize):
        # xyCoords = Util.read_tsv(csvFile)
        # x = map(float, xyCoords["x"])
        # y = map(float, xyCoords["y"])
        idList = list(articleCoords.keys())
        x = np.array([float(articleCoords[featureID]["x"]) for featureID in idList])
        y = np.array([float(articleCoords[featureID]["y"]) for featureID in idList])
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

    def _get_contours(self, coordinates):
        CS = self._calc_contour(coordinates, 35)
        plys = []
        for i in range(len(CS.collections)):
            shapes = []
            for j in range(len(CS.collections[i].get_paths())):
                p = CS.collections[i].get_paths()[j]
                v = p.vertices
                shapes.append(v)
            plys.append(shapes)

        copy_lst = copy.deepcopy(plys)
        count = 0
        for layers in copy_lst:
            newShape = []
            for shapes in layers:
                bbPath = mplPath.Path(shapes)
                for others in layers:
                    if (shapes[0][0] != others[0][0]) \
                       and (shapes[0][1] != others[0][1]) \
                       and bbPath.contains_point((others[0][0], others[0][1])):
                        if len(newShape) == 0:
                            newShape.append(shapes)
                            self._remove_array(plys[count], shapes)

                        newShape.append(others)
                        self._remove_array(plys[count], others)
            if len(newShape) != 0:
                plys.append(newShape)
            count += 1
        return plys

    def _gen_contour_features(self, coordinates):
        featureAr = []
        polyGroups = []
        for group in self._get_contours(coordinates):
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

    def makeContourFeatureCollection(self, coordinates, outputFilename):
        featureAr = self._gen_contour_features(coordinates)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(outputFilename, "w") as writeFile:
            writeFile.write(textDump)

