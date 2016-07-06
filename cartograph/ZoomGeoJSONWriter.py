from geojson import Feature, FeatureCollection
from geojson import dumps, Point


class ZoomGeoJSONWriter:
    def __init__(self, featureDict):
        self.articleData = featureDict

    def generateZoomJSONFeature(self, filename):
        featureAr = []
        zoomFeatures = list(self.articleData.values())

        for pointInfo in zoomFeatures:
            pointTuple = (float(pointInfo['x']), float(pointInfo['y']))
            newPoint = Point(pointTuple)
            properties = {'maxZoom': int(pointInfo['maxZoom']),
                          'popularity': float(pointInfo['popularity']),
                          'cityLabel': str(pointInfo['name'])
                          }
            newFeature = Feature(geometry=newPoint, properties=properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(filename, 'w') as writeFile:
            writeFile.write(textDump)
