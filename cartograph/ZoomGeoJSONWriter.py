from geojson import Feature, FeatureCollection
from geojson import dumps, Point
import Config
import Util

class ZoomGeoJSONWriter:
    def __init__(self, featDict):
        self.articleData = featDict

    def generateZoomJSONFeature(self, filename):
        featureAr = []
        zoomDict = self.articleData
        zoomFeatures = list(zoomDict.values())

        for pointInfo in zoomFeatures:
            pointTuple = (float(pointInfo['x']),float(pointInfo['y']))
            newPoint = Point(pointTuple)
            properties = {'maxZoom':int(pointInfo['maxZoom']), 
                          'popularity':float(pointInfo['popularity']),
                          'cityLabel':str(pointInfo['name']),
                          'popBinScore':int(pointInfo['popBinScore'])
                          }
            newFeature = Feature(geometry=newPoint, properties=properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(filename, 'w') as writeFile:
            writeFile.write(textDump)
