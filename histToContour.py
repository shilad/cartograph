import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage
import copy


def calcContour(csvFile, binSize):
    xyCoords = np.genfromtxt(csvFile, delimiter=',', usecols=(1, 2), skip_header=1)
    x = xyCoords[:, 0]
    y = xyCoords[:, 1]
    contBuffer = 20

    H, yedges, xedges = np.histogram2d(y, x, bins=binSize,
                                       range=[[np.min(x) - contBuffer, np.max(x) + contBuffer], [np.min(y) - contBuffer, np.max(y) + contBuffer]])
    extent = [xedges.min(), xedges.max(), yedges.min(), yedges.max()]

    smoothH = scipy.ndimage.zoom(H, 4)
    smoothH[smoothH < 0] = 0
    return plt.contour(smoothH, extent=extent)

CS = calcContour('./data/data.csv', 35)

def removearray(L,arr):
    ind = 0
    size = len(L)
    while ind != size and not np.array_equal(L[ind],arr):
        ind += 1
    if ind != size:
        L.pop(ind)
    else:
        raise ValueError('array not found in list.')

def getContours():
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
                if (shapes[0][0] != others[0][0]) and (shapes[0][1] != others[0][1]) and bbPath.contains_point((others[0][0], others[0][1])):
                    if len(newShape) == 0:
                        newShape.append(shapes)
                        removearray(plys[count], shapes)

                    newShape.append(others)
                    removearray(plys[count], others)

        if len(newShape) != 0:
            plys.append(newShape)
        count += 1
    return plys
