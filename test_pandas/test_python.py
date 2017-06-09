import filecmp

import math
import pandas as pd
import numpy as np
from pprint import pprint

from geojson import Point, Feature, FeatureCollection

from  cartograph import Utils, Config
import luigi
import json


import scipy.stats as sps
import shapely.geometry as shply
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.path as mplPath
import scipy.ndimage as spn
from cartograph.BorderGeoJSONWriter import CreateContinents
from cartograph.Regions import MakeRegions
from cartograph.LuigiUtils import MTimeMixin, TimestampedLocalTarget
from geojson import Feature, FeatureCollection
from geojson import dumps, MultiPolygon
from collections import defaultdict
from shapely.geometry import Point



config = Config.initTest()

#For CoordinatesGeoJSONWriter in CalculateZPop - I think this method is not used
def readfeat_try():
    points = Utils.read_features('./data/simple/tsv/zpop.tsv', './data/simple/tsv/coordinates.tsv', './data/simple/tsv/numberedClusters.tsv', './data/ext/simple/names.tsv', required=('x', 'y', 'name', 'zpop', 'cluster'))
    features = []
    for id, pointInfo in points.items():
        pointTuple = (float(pointInfo['x']), float(pointInfo['y']))
        newPoint = Point(pointTuple)
        properties = {'id': id,
                              'zpop': float(pointInfo['zpop']),
                               'name': str(pointInfo['name']),
                               'x': float(pointInfo['x']),
                               'y': float(pointInfo['y']),
                               'clusterid': pointInfo['cluster']
                               }
        features.append(Feature(geometry=newPoint, properties=properties))
    collection = FeatureCollection(features)
    return(collection)

#For CoordinatesGeoJSONWriter in CalculateZPop - I think this method is not used
def geoCodePandas():
    zpop = pd.read_table('./data/simple/tsv/zpop.tsv', index_col='index')
    coor = pd.read_table('./data/simple/tsv/coordinates.tsv', index_col='index')
    nClusters = pd.read_table('./data/simple/tsv/numberedClusters.tsv', index_col='index')
    names = pd.read_table('./data/ext/simple/names.tsv', index_col='id' )

    final = zpop.merge(coor, left_index = True, right_index= True)
    final = final.merge(nClusters, left_index = True, right_index = True)
    final = final.merge(names, left_index = True, right_index = True)

    #print(final.to_dict('index'))
    #for index
    features = []
    for row in final.itertuples():
        pointTuple = (row[2], row[3])
        newPoint = Point(pointTuple)
        properties = {'id': row[0],
                      'zpop': row[1],
                      'name': row[5],
                      'x': row[2],
                      'y': row[3],
                      'clusterid':row[4]
                      }
        features.append(Feature(geometry=newPoint, properties=properties))
    collection = FeatureCollection(features)
    #print(collection)
    return collection


#For ZPopTask in CalculateZPop - Working
def calcZPopPandas(filepath):
    feats = pd.read_table(filepath, index_col='id')
    feats = feats.sort_values(by='popularity', ascending=False)
    def log4(x): return np.log2(x) / np.log2(4)
    feats['zpop'] = log4(np.arange(feats.shape[0])/ 2.0 + 1.0)
    feats['zpop'].to_csv('testPopPanda.tsv', sep='\t', index_label = 'index', header='zpop' )
    return feats

def contour_sampleOri():
    required = ('cluster', 'vector', 'x', 'y', 'keep')
    featuresDict = Utils.read_features(config.getSample("TestFiles", 'article_coordinates'),
                                       config.getSample("TestFiles",
                                                        "clusters_with_id"),
                                       config.getSample("TestFiles",
                                                        "denoised_with_id"),
                                       config.getSample("TestFiles",
                                                        "vecs_with_id"),
                                       required=required)

    return featuresDict

#pprint(contour_sampleOri())


def contour_samplePandas():
    coor = pd.read_table(config.getSample("GeneratedFiles", 'article_coordinates'),   index_col='index')

    clusters = pd.read_table(config.getSample("GeneratedFiles","clusters_with_id"), index_col='index', dtype={'cluster': 'str'})
    #clusters['cluster']=clusters['cluster'].astype('str') #cluster needs to be a string and not a integer to work
    denoised = pd.read_table(config.getSample("GeneratedFiles","denoised_with_id"), index_col='index')
    denoised = denoised.filter(regex = '^[0-9]+$', axis=0) #filter out water points
    denoised.index = denoised.index.map(np.int64) #need to convert the index to int64 for merge

    vecs = pd.read_table(config.getSample("GeneratedFiles","vecs_with_id"), skip_blank_lines=True, skiprows=1, header=None)
    vecs['vectorTemp'] = vecs.iloc[:, 1:].apply(lambda x: tuple(x), axis=1) #join all vector columns into same column as a tuple
    vecs.drop(vecs.columns[1:-1], axis=1, inplace=True) # drop all columns but the index and the vectorTemp column
    vecs.columns=['index', 'vector']
    vecs = vecs.set_index('index')

    #below merge all files
    final = coor.merge(clusters, left_index=True, right_index=True)
    final = final.merge(denoised, left_index=True, right_index=True)
    final = final.merge(vecs, left_index=True, right_index=True)

    return final
#print(contour_samplePandas())




class ContourCreator:
    '''
    Creates the centroid and density contours for the map
    based on the wikipedia page placement and by writing them
    out to geojson files.
    '''

    def __init__(self, numClusters, binSize):
        self.numClusters = numClusters
        self.binSize = binSize

    def buildContours(self, featureDict, countryFile):
        '''
        Runs class methods to define class variables for
        other methods in the class.
        '''
        self.xs, self.ys, self.vectors = self._sortClustersInBorders(featureDict, self.numClusters, countryFile)
        self.centralities = self._centroidValues()
        self.countryFile = countryFile
        self.CSs = []
        self.CSs.append(self._densityCalcContour())
        self.CSs.append(self._centroidCalcContour())

    def buildContours2(self, featureDict, countryFile):
        '''
        Runs class methods to define class variables for
        other methods in the class.
        '''
        self.xs, self.ys, self.vectors = self._sortClustersInBordersOri(featureDict, self.numClusters, countryFile)
        self.centralities = self._centroidValues()
        self.countryFile = countryFile
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



        # allBordersDict = {}
        # for feature in bordersData['features']:
        #     poly = shply.shape(feature['geometry']).simplify(0.01)
        #     clusterId = feature['properties']['clusterId']
        #     assert(clusterId)
        #     allBordersDict[clusterId] = poly

        xs = defaultdict(list)
        ys = defaultdict(list)
        vectors = defaultdict(list)

        #keys = featureDict.sort_index().index #sorted(featureDict.keys())


        #keys = []
        # for index in featureDict:
        #     if 'keep' not in featureDict[index]:
        #         count += 1
        #     elif 'cluster' not in featureDict[index]:
        #         count += 1
        #     elif 'x' not in featureDict[index]:
        #         count += 1
        #     else:
        #         keys.append(index)
        # print '%d of %d were bad keys' % (count, len(featureDict))

        #featureDict = { k: featureDict[k] for k in keys }   # filter out bad keys
        count = 0
        for row in featureDict.itertuples():
            if count % 10000 == 0:
                print 'doing', count, 'of', featureDict.shape[0]
            if row[4] == False: continue
            c = row[3]
            xs[c].append(row[1])
            ys[c].append(row[2])
            vectors[c].append(row[5])
            count += 1
        return xs, ys, vectors
        # for i, index in enumerate(keys):
        #     if i % 10000 == 0:
        #         print 'doing', i, 'of', len(keys)
        #     pointInfo = featureDict[index]
        #     if pointInfo['keep'] != 'True' or pointInfo.get('cluster') in (None, ''): continue
        #     c = pointInfo['cluster']
        #     xy = Point(float(pointInfo['x']), float(pointInfo['y']))
        #     # poly = allBordersDict.get(c)
        #     # if poly and poly.contains(xy):
        #     xs[c].append(xy.x)
        #     ys[c].append(xy.y)
        #     vectors[c].append(pointInfo['vector'])
        #
        # return xs, ys, vectors

    def _sortClustersInBordersOri(self, featureDict, numClusters, bordersGeoJson):  # numClusters not used?
        '''
        Sorts through the featureDict to find the points and vectors
        that correspond to each individual country and returns lists
        with those variables in the correct country spot. This only catches
        the points that are within the country borders.
        '''
        with open(bordersGeoJson) as f:
            bordersData = json.load(f)

        # Is this doing anything?
       # allBordersDict = {}
        #for feature in bordersData['features']:
         #   poly = shply.shape(feature['geometry']).simplify(0.01)
          #  clusterId = feature['properties']['clusterId']
           # assert (clusterId)
            #allBordersDict[clusterId] = poly

        xs = defaultdict(list)
        ys = defaultdict(list)
        vectors = defaultdict(list)
        keys = sorted(featureDict.keys())  # do not need this?

        count = 0
        keys = []
        for index in featureDict:
            if 'keep' not in featureDict[index]:
                count += 1
            elif 'cluster' not in featureDict[index]:
                count += 1
            elif 'x' not in featureDict[index]:
                count += 1
            else:
                keys.append(index)
        print '%d of %d were bad keys' % (count, len(featureDict))

        featureDict = {k: featureDict[k] for k in keys}  # filter out bad keys

        for i, index in enumerate(keys):
            if i % 10000 == 0:
                print 'doing', i, 'of', len(keys)
            pointInfo = featureDict[index]
            if pointInfo['keep'] != 'True' or pointInfo.get('cluster') in (None, ''): continue
            c = pointInfo['cluster']
            xy = Point(float(pointInfo['x']), float(pointInfo['y']))
            # poly = allBordersDict.get(c)
            # if poly and poly.contains(xy):
            xs[c].append(xy.x)
            ys[c].append(xy.y)
            vectors[c].append(pointInfo['vector'])

        return xs, ys, vectors

    def _centroidValues(self):
        '''
        Gets the centroid values of each vector by first finding the centroid
        through the mean of all vectors in a group. Then using dot product to
        compare each vector to the centroid and find each individual
        centroid value.
        '''
        centralities = {}
        for c, clusterVecs in self.vectors.items():
            centroid = np.mean(clusterVecs, axis=0)
            centralities[c] = [centroid.dot(v) for v in clusterVecs]
        return centralities

    def _centroidCalcContour(self):
        '''
        Creates the contours based off of centroids using binned_statistic_2d
        '''
        CSs = {}
        for c in self.xs:
            x = self.xs[c]
            y = self.ys[c]
            values = self.centralities[c]
            assert(len(x) == len(y) == len(values))
            if len(x) < 2: continue  # essentially empty!
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
            CSs[c] = plt.contour(smoothH, extent=extent)

        return CSs

    def _densityCalcContour(self):
        '''
        Creates the contours based off of density using histogram2d
        '''
        CSs = {}
        for c in self.xs:
            x = self.xs[c]
            y = self.ys[c]
            values = self.centralities[c]
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
            CSs[c] = plt.contour(smoothH, extent=extent)

        return CSs

    def _getContours(self, CSs):
        '''
        Extracts the contours from CS.collections.get_paths to
        separate each contour by layer.
        '''
        plyList = {}
        for c, CS in CSs.items():
            plys = []
            for i in range(len(CS.collections)):
                shapes = []
                for j in range(len(CS.collections[i].get_paths())):
                    p = CS.collections[i].get_paths()[j]
                    v = p.vertices
                    shapes.append(v)
                plys.append(shapes)
            plyList[c] = plys
        return plyList

    def _cleanContours(self, CSs):
        '''
        This cuts off the edges of the contours that go over the edges
        of a country so it looks tidier. This method uses shapely
        geometric and intersection features.
        '''
        js = json.load(open(self.countryFile, 'r'))
        plyList = self._getContours(CSs)

        newPlys = {}
        #print(plyList)
        for clusterFeatures in js['features']:
            clusterId = clusterFeatures['properties']['clusterId']
            assert(clusterId)
            print(clusterId)
            if clusterId not in plyList: continue
            print('here')
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
            newPlys[clusterId] = newClusterContours

        return newPlys

    def _genContourPolygons(self, CSs):
        '''
        Implements the Contour and Polygon classes to sort out the
        holes before creating geojson MultiPolygon
        Features for each Contour.
        '''
        newPlys = self._cleanContours(CSs)
        # newPlys = CSs
        countryGroup = {}
        for clusterId, plys in newPlys.items():
            contourList = []
            for group in plys:
                contour = Contour(group)
                contour.createHoles()
                contourList.append(contour)
            countryGroup[clusterId] = contourList

        featureAr = []
        for clusterId, contourList in countryGroup.items():
            for index, contour in enumerate(contourList):
                geoPolys = []
                for polygon in contour.polygons:
                    geoPolys.append(polygon.points)
                newMultiPolygon = MultiPolygon(geoPolys)
                props = {
                    "contourNum": index,
                    "clusterId": clusterId,
                    "contourId": str(clusterId) + '_' + str(index)
                }
                newFeature = Feature(geometry=newMultiPolygon, properties=props)
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


#Work on contour next week :)

def contour_calcsPanda():
    numClusters = config.getint("PreprocessingConstants", "num_clusters")
    binSize = config.getint("PreprocessingConstants", "contour_bins")
    countryBorders = config.get("MapData", "countries_geojson")

    feats = contour_samplePandas()

    contour = ContourCreator(numClusters, binSize)

    contour.xs, contour.ys, contour.vectors = contour._sortClustersInBorders(feats, contour.numClusters, countryBorders)
    contour.centralities = contour._centroidValues()
    contour.countryFile = countryBorders
    contour.CSs = []
    contour.CSs.append(contour._densityCalcContour())
    contour.CSs.append(contour._centroidCalcContour())
    contour.makeContourFeatureCollection([config.get("MapData", "density_contours_geojson"),config.get("MapData", "centroid_contours_geojson")])
    return contour
    #self.countryFile = countryFile
    #self.CSs = []
    #self.CSs.append(self._densityCalcContour())
    #self.CSs.append(self._centroidCalcContour())
    #contour.buildContours(feats ,countryBorders)
    #contour.makeContourFeatureCollection(['./data/test/mapdata/density_contours_geojson_test', './data/test/mapdata/centroid_contours_geojson_test'])
#pprint(contour_calcsPanda()[2])

def contour_calcsOri():
    numClusters = config.getint("PreprocessingConstants", "num_clusters")
    binSize = config.getint("PreprocessingConstants", "contour_bins")
    countryBorders = config.get("MapData", "countries_geojson")

    contour = ContourCreator(numClusters, binSize)
    feats = contour_sampleOri()

    contour.xs, contour.ys, contour.vectors = contour._sortClustersInBordersOri(feats, contour.numClusters, countryBorders)
    contour.centralities = contour._centroidValues()
    contour.countryFile = countryBorders
    contour.CSs = []
    contour.CSs.append(contour._densityCalcContour())
    contour.CSs.append(contour._centroidCalcContour())
    contour.makeContourFeatureCollection(['./data/test/geojson/density_contours_geojson_test.geojson',
                                          './data/test/geojson/centroid_contours_geojson_test.geojson'])
    return contour



def test_contourTemp():
    cPanda = contour_calcsPanda()
    cOri = contour_calcsOri()
    print 'pandasX', cPanda.xs
    print 'pandasY', cPanda.ys
    print 'oriX', cOri.xs
    print 'oriY', cOri.ys

    #pprint((cPanda.vectors['2']))

    #pprint((cOri.vectors['2']))
  #  print 'oriV', (cOri.vectors['1'][0])
    print('len', len(cPanda.vectors['2']))
    np.testing.assert_allclose(cPanda.vectors['2'][3], cOri.vectors['2'][0])
    for key in cPanda.vectors.keys():
        print('key', key)
        for i in range(len(cPanda.vectors[key])):
            compP = np.sort(cPanda.vectors[key],axis=None)
            compO = np.sort(cOri.vectors[key], axis = None)
            print('index', i)
            np.testing.assert_allclose(compP[i], compO[i])
    print('panda')
    pprint(cPanda.centralities)
    print('ori')
    pprint(cOri.centralities)
    pprint(cPanda.CSs[0])
#test_contourTemp()
print('Panda')
#cPanda = contour_calcsPanda()
#pprint((cPanda.CSs[0][0]))
#pL = cPanda._getContours(cPanda.CSs[0])
print('Ori')
#cOri = contour_calcsOri()
#pLO = cOri._getContours(cOri.CSs[0])

#pprint(sorted(pL)[:5])
#pprint(sorted(pLO)[:5])
#pprint(contour_calcsOri())
#pprint((cOri.CSs[1]['1']))

#how to test? figutre out how to unit test this
#pprint(filecmp.cmp('./data/test/mapdata/centroid_contours_geojson_test.geojson', './data/simple/geojson/centroidContourData.geojson'))

def test_contour():
    contour_calcsPanda()
    #contour_calcsOri()
    with open(config.get("MapData", "centroid_contours_geojson")) as data_filePandas:
        cPanda = json.load(data_filePandas)
    with open('./data/ext/test-orig/geojson/centroid_contours_geojson_test.geojson')  as  data_fileOri:
        cOri = json.load(data_fileOri)
    cPandaProp = []
    cPandaCoor = []
    cOriProp = []
    cOriCoor = []
    for feature in cPanda['features']:
        cPandaProp.append(feature['properties'])
        cPandaCoor.append(np.sort(feature['geometry']['coordinates'], axis=None))
    for feature in cOri['features']:
        cOriProp.append(feature['properties'])
        cOriCoor.append(np.sort(feature['geometry']['coordinates'], axis= None))
    for i in range(len(cPandaCoor)):
        for j in range(len(cPandaCoor[i])):
            np.testing.assert_allclose(cPandaCoor[i][j], cOriCoor[i][j])


    #assert cPandaCoor == cOriCoor
    assert cPandaProp == cOriProp
    return cOriCoor, cPandaCoor

def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

r = test_contour()
print('ori')
pprint(r[0])
print('panda')
pprint(r[1])



#pprint(r[1])