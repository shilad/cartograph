import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage as spn
from geojson import Feature, FeatureCollection
from geojson import dumps, MultiPolygon
import scipy.stats as sps
import json
import shapely.geometry as shply
from collections import defaultdict
from shapely.geometry import mapping, Point


class ContourCreator:

    def __init__(self, numClusters):
        self.numClusters = numClusters
        pass

    def buildContours(self, featureDict, countryFile):
        self.xs, self.ys, self.vectors = self._sortClustersInBorders(featureDict, self.numClusters, countryFile)
        self.centralities = self._centroidValues()
        self.countryFile = countryFile
        self.binSize = 200
        self.density_CSs = self._densityCalcContour()
        self.centroid_CSs = self._centroidCalcContour()


    def _sortClustersInBorders(self, featureDict, numClusters, bordersGeoJson):
        with open(bordersGeoJson) as f:
            bordersData = json.load(f)

        allBordersDict = defaultdict(dict)
        for feature in bordersData['features']:
            poly = shply.shape(feature['geometry'])
            cluster =feature['properties']['clusterNum']
            allBordersDict[str(cluster)] = poly

        xs = [[] for i in range(numClusters)]
        ys = [[] for i in range(numClusters)]
        vectors = [[] for i in range(numClusters)]
        keys = featureDict.keys()

        for i, index in enumerate(keys):
            if i % 1000 == 0:
                print('doing', i, 'of', len(keys))
            pointInfo = featureDict[index]
            if pointInfo['keep'] != 'True' or 'cluster' not in pointInfo: continue
            c = int(pointInfo['cluster'])
            xy = Point(float(pointInfo['x']),float(pointInfo['y']))
            poly = allBordersDict[str(c)]
            if poly.contains(xy):
                xs[c].append(float(pointInfo['x']))
                ys[c].append(float(pointInfo['y']))
                vectors[c].append(pointInfo['vector'])

        return xs, ys, vectors

    def _centroidValues(self):
        centralities = []
        for vector in self.vectors:
            centroid = np.mean(vector, axis=0)
            dotValues = []
            for vec in vector:
                dotValues.append(centroid.dot(vec))
            centralities.append(dotValues)

        return centralities

    def _centroidCalcContour(self):
        CSs = []
        for (x, y, values) in zip(self.xs, self.ys, self.centralities):
            if not x: continue
            centrality, yedges, xedges, binNumber = sps.binned_statistic_2d(y, x,
                                            values,
                                            statistic='mean',
                                            bins=self.binSize,
                                            range=[[np.min(y),
                                            np.max(y)],
                                            [np.min(x),
                                            np.max(x)]])
            for i in range(len(centrality)):
                centrality[i] = np.nan_to_num(centrality[i])

            centrality = spn.filters.gaussian_filter(centrality, 2)
            extent = [xedges.min(), xedges.max(), yedges.min(), yedges.max()]

            smoothH = spn.zoom(centrality, 4)
            smoothH[smoothH < 0] = 0
            CSs.append(plt.contour(smoothH, extent=extent))

        return CSs

    def _densityCalcContour(self):
        CSs = []
        for (x, y) in zip(self.xs, self.ys):
            if not x: continue
            H, yedges, xedges = np.histogram2d(y, x,
                                               bins=self.binSize,
                                               range=[[np.min(y),
                                                      np.max(y)],
                                                      [np.min(x),
                                                      np.max(x)]])

            H = spn.filters.gaussian_filter(H, 2)
            extent = [xedges.min(), xedges.max(), yedges.min(), yedges.max()]

            smoothH = spn.zoom(H, 4)
            smoothH[smoothH < 0] = 0
            CSs.append(plt.contour(smoothH, extent=extent))

        return CSs

    def _getContours(self, CSs):
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

    def _cleanContours(self, CSs):
        js = json.load(open(self.countryFile, 'r'))
        plyList = self._getContours(CSs)

        newPlys = []
        for (clusterId, clusterFeatures) in enumerate(js['features']):
            clusterGeom = shply.shape(clusterFeatures['geometry']).buffer(0.0)
            newClusterContours = []
            for clusterCounters in plyList[clusterId]:
                newPolygons = []
                for polygon in clusterCounters:
                    if len(polygon) < 3: continue
                    shplyPoly = shply.Polygon(polygon).buffer(0.0)
                    newPolygon = shplyPoly.intersection(clusterGeom)
                    if newPolygon.geom_type == 'Polygon':
                        newPolygon = [newPolygon]
                    for p in newPolygon:
                        newCoords = p.exterior.coords
                        if len(newCoords) > 0:
                            newPolygons.append(newCoords)
                        newIntCoords = p.interiors
                        if len(newIntCoords) > 0:
                            for ring in newIntCoords:
                                newPolygons.append(ring.coords)
                if len(newPolygons) > 0:
                    newClusterContours.append(newPolygons)
            newPlys.append(newClusterContours)

        return newPlys

    def _genContourPolygons(self, CSs):
        newPlys = self._cleanContours(CSs)
        countryGroup = []
        for plys in newPlys:
            contourList = []
            for group in plys:
                contour = Contour(group)
                contour.createHoles()
                contourList.append(contour)
            countryGroup.append(contourList)

        featureAr = []
        for clusterNum, contourList in enumerate(countryGroup):
            for index, contour in enumerate(contourList):
                geoPolys = []
                for polygon in contour.polygons:
                    geoPolys.append(polygon.points)
                newMultiPolygon = MultiPolygon(geoPolys)
                newFeature = Feature(geometry=newMultiPolygon, properties={"contourNum": index, "clusterNum": clusterNum, "identity": str(index) + str(clusterNum)})
                featureAr.append(newFeature)

        return featureAr

    def makeDensityContourFeatureCollection(self, outputfilename):
        featureAr = self._genContourPolygons(self.density_CSs)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(outputfilename, "w") as writeFile:
            writeFile.write(textDump)

    def makeCentroidContourFeatureCollection(self, outputfilename):
        featureAr = self._genContourPolygons(self.centroid_CSs)
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
                if poly is not otherPolys \
                   and path.contains_points(otherPolys.points[0]).all():
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
