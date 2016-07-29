import luigi
import json
import Coordinates
import Popularity
import Config
import Utils
import scipy.stats as sps
import shapely.geometry as shply
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage as spn
from BorderGeoJSONWriter import CreateContinents
from Regions import MakeRegions
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from geojson import Feature, FeatureCollection
from geojson import dumps, MultiPolygon
from collections import defaultdict
from shapely.geometry import Point


class ContourCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class CreateContours(MTimeMixin, luigi.Task):
    '''
    Make contours based on density of points inside the map
    Generated as geojson data for later use inside map.xml
    '''
    def requires(self):
        config = Config.get()
        return (Coordinates.CreateSampleCoordinates(),
                Popularity.SampleCreator(config.get("ExternalFiles",
                                                    "vecs_with_id")),
                ContourCode(),
                CreateContinents(),
                MakeRegions())

    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("MapData", "centroid_contours_geojson")),
                TimestampedLocalTarget(config.get("MapData", "density_contours_geojson")))

    def run(self):
        config = Config.get()
        featuresDict = Utils.read_features(config.getSample("GeneratedFiles",
                                                     "article_coordinates"),
                                           config.getSample("GeneratedFiles",
                                                     "clusters_with_id"),
                                           config.getSample("GeneratedFiles",
                                                     "denoised_with_id"),
                                           config.getSample("ExternalFiles",
                                                     "vecs_with_id"))
        for key in featuresDict.keys():
            if key[0] == "w":
                del featuresDict[key]

        numClusters = config.getint("PreprocessingConstants", "num_clusters")

        countryBorders = config.get("MapData", "countries_geojson")

        contour = ContourCreator(numClusters)
        contour.buildContours(featuresDict, countryBorders)
        contour.makeContourFeatureCollection([config.get("MapData", "density_contours_geojson"),config.get("MapData", "centroid_contours_geojson")])


class ContourCreator:
    '''
    Creates the centroid and density contours for the map
    based on the wikipedia page placement and by writing them
    out to geojson files.
    '''

    def __init__(self, numClusters):
        self.numClusters = numClusters

    def buildContours(self, featureDict, countryFile):
        '''
        Runs class methods to define class variables for
        other methods in the class.
        '''
        self.xs, self.ys, self.vectors = self._sortClustersInBorders(featureDict, self.numClusters, countryFile)
        self.centralities = self._centroidValues()
        self.countryFile = countryFile
        self.binSize = 200
        self.CSs = []
        self.CSs.append(self._densityCalcContour())
        self.CSs.append(self._centroidCalcContour())

    def _sortClustersInBorders(self, featureDict, numClusters, bordersGeoJson):
        '''
        Sorts through the featureDict to find the points and vectors
        that correspond to each individual country and returns lists
        with those variables in the correct country spot. This only catches
        the points that are within the country borders.
        '''
        with open(bordersGeoJson) as f:
            bordersData = json.load(f)

        allBordersDict = defaultdict(dict)
        for feature in bordersData['features']:
            poly = shply.shape(feature['geometry'])
            cluster = feature['properties']['clusterNum']
            allBordersDict[str(cluster)] = poly

        xs = [[] for i in range(numClusters)]
        ys = [[] for i in range(numClusters)]
        vectors = [[] for i in range(numClusters)]
        keys = featureDict.keys()

        count = 0
        badKeys = []
        for index in keys:
            if 'keep' not in featureDict[index].keys():
                count += 1
                badKeys.append(index)
            elif 'cluster' not in featureDict[index].keys():
                count += 1
                badKeys.append(index)
            elif 'x' not in featureDict[index].keys():
                count += 1
                badKeys.append(index)

        for key in badKeys:
            keys.remove(key)
            del featureDict[key]

        for i, index in enumerate(keys):
            if i % 10000 == 0:
                print 'doing', i, 'of', len(keys)
            pointInfo = featureDict[index]
            if pointInfo['keep'] != 'True' or 'cluster' not in pointInfo: continue
            c = int(pointInfo['cluster'])
            xy = Point(float(pointInfo['x']), float(pointInfo['y']))
            poly = allBordersDict[str(c)]
            if poly.contains(xy):
                xs[c].append(float(pointInfo['x']))
                ys[c].append(float(pointInfo['y']))
                vectors[c].append(pointInfo['vector'])

        return xs, ys, vectors

    def _centroidValues(self):
        '''
        Gets the centroid values of each vector by first finding the centroid
        through the mean of all vectors in a group. Then using dot product to
        compare each vector to the centroid and find each individual
        centroid value.
        '''
        centralities = []
        for vector in self.vectors:
            centroid = np.mean(vector, axis=0)
            dotValues = []
            for vec in vector:
                dotValues.append(centroid.dot(vec))
            centralities.append(dotValues)

        return centralities

    def _centroidCalcContour(self):
        '''
        Creates the contours based off of centroids using binned_statistic_2d
        '''
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
        '''
        Creates the contours based off of density using histogram2d
        '''
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
        '''
        Extracts the contours from CS.collections.get_paths to
        separate each contour by layer.
        '''
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
        '''
        This cuts off the edges of the contours that go over the edges
        of a country so it looks tidier. This method uses shapely
        geometric and intersection features.
        '''
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
        '''
        Implements the Contour and Polygon classes to sort out the
        holes before creating geojson MultiPolygon
        Features for each Contour.
        '''
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

    def makeContourFeatureCollection(self, outputfilename):
        '''
        Creates contours, it sends
        the CS that corresponds with the contour type off. Writes
        it out to a geojson file.
        '''
        for i, filename in enumerate(outputfilename):
            featureAr = self._genContourPolygons(self.CSs[i])
            collection = FeatureCollection(featureAr)
            textDump = dumps(collection)
            with open(filename, "w") as writeFile:
                writeFile.write(textDump)


class Contour:
    '''
    This class represents one contour layer.
    It uses the Polygon class to sort through all the polygons
    in the layer and figure out where the holes are.
    '''

    def __init__(self, shapes):
        '''
        Converts shapes to be used as self.polygons for the
        rest of the class.
        '''
        self.polygons = self._generatePolygons(shapes)

    def _generatePolygons(self, shapes):
        '''
        Takes the polygons out of their numpy array form
        so that we can give them to geojson properly.
        '''
        polys = set()
        for group in shapes:
            points = []
            for pt in group:
                points.append((pt[0], pt[1]))
            polys.add(Polygon(points))
        return polys

    def createHoles(self):
        '''
        Finds the polygons that are inside other polygons in this contour
        layer then sets them as children of the polygon that they are
        inside of to create holes.
        '''
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
        '''
        Creates holes in all of the polygons in the layer.
        '''
        for poly in self.polygons:
            poly.collapseChildren()


class Polygon:
    '''
    This class represents one polygon in one contour layer.
    '''

    def __init__(self, points):
        '''
        Initializes the points in a list in case the polygon has children
        which means that the location of the child polygon is inside of
        the parent polygon.
        '''
        self.points = [points]
        self.children = set()

    def collapseChildren(self):
        '''
        Add's the children's points to this polygon's points so that
        when Mapnik reads it in, it is seen as a hole in this polygon.
        '''
        for child in self.children:
            self.points.append(child.points[0])
