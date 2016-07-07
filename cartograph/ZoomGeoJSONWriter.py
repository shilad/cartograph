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
                          'popularity':float(pointInfo['popularity']),
                          'cityLabel':str(pointInfo['name'])
                          }
            newFeature = Feature(geometry=newPoint, properties=properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(filename, 'w') as writeFile:
            writeFile.write(textDump)

    def writeZoomTSV(self):
        zoomDict = Util.read_features(config.FILE_NAME_NUMBERED_ZOOM,
                config.FILE_NAME_NUMBERED_NAMES)
        #THIS NEEDS TO CHANGE TO BE PART OF THE CONFIG FILE, BUT I'M HARDCODING IT FOR NOW
        filepath = "./web/data/named_zoom.tsv"
        with open(filepath, "a") as writeFile:
            #hardcoded and inelegant, but it works and it's just a data file that only needs to be generated once so...
            writeFile.write('name\tmaxZoom\n')
            for entry in zoomDict:
                name = zoomDict[entry]['name']
                zoom = zoomDict[entry]['maxZoom']
                writeFile.write(name + "\t" + zoom + "\n")
