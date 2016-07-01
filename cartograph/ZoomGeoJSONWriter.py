from geojson import Feature, FeatureCollection
from geojson import dumps, Point
import Config
import Util

config = Config.BAD_GET_CONFIG()

class ZoomGeoJSONWriter:
    def __init__(self):
        self.articleData = self._readInArticles()

    def _readInArticles(self):
        return Util.read_features(config.FILE_NAME_NUMBERED_ZOOM,
                config.FILE_NAME_ARTICLE_COORDINATES,
                config.FILE_NAME_NUMBERED_POPULARITY,
                config.FILE_NAME_NUMBERED_NAMES)

    def generateZoomJSONFeature(self, filename):
        featureAr = []
        zoomDict = self._readInArticles()
        zoomFeatures = list(zoomDict.values())

        for pointInfo in zoomFeatures:
            pointTuple = (float(pointInfo['x']),float(pointInfo['y']))
            newPoint = Point(pointTuple)
            properties = {'maxZoom':int(pointInfo['maxZoom']), 
                          'popularity':int(pointInfo['popularity']),
                          'cityLabel':str(pointInfo['name'])
                          }
            newFeature = Feature(geometry=newPoint, properties=properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(filename, 'w') as writeFile:
            writeFile.write(textDump)
