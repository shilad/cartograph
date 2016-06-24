from geojson import Feature, FeatureCollection
from geojson import dumps, Point
import Config
import Util

config = Config.BAD_GET_CONFIG()


class TopTitlesGeoJSONWriter:
    def __init__(self, numArticles):
        self.numArticles = numArticles
        self.articleData = self._readInArticles()

    def _readInArticles(self):
        return Util.read_features(config.FILE_NAME_NUMBERED_NAMES,
                                  config.FILE_NAME_NUMBERED_POPULARITY,
                                  config.FILE_NAME_ARTICLE_COORDINATES)

    def getTopArticles(self):
        allArticles = Util.sort_by_feature(self.articleData, "popularity")
        return allArticles[:self.numArticles]

    def generateJSONFeature(self, filename):
        featureAr = []
        topArticles = self.getTopArticles()
        for article in topArticles:
            articleDict = article[1]
            pointTuple = (float(articleDict["x"]), float(articleDict["y"]))
            newPoint = Point(pointTuple)
            properties = {'titleLabel': articleDict["name"]}
            newFeature = Feature(geometry=newPoint, properties=properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(filename, "w") as writeFile:
            writeFile.write(textDump)
