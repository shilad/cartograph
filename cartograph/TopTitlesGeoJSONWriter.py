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
                                  config.FILE_NAME_ARTICLE_COORDINATES,
                                  config.FILE_NAME_NUMBERED_CLUSTERS)

    def getTopCountryArticles(self):
        sortedByClust = [[] for i in range(config.NUM_CLUSTERS)]
        articleDict = self.articleData
        topCountryArticles = []
        for key in articleDict:
            c = int(articleDict[key]['cluster'])
            sortedByClust[c].append((key, articleDict[key]))
        for clustArticles in sortedByClust:
            clustArticles.sort(key=lambda x: (x[1]['popularity']), reverse=True)
            topCountryArticles = topCountryArticles + clustArticles[:self.numArticles]
        return(topCountryArticles)

    def getTopArticles(self):
        allArticles = Util.sort_by_feature(self.articleData, "popularity")
        return allArticles[:self.numArticles]

    def generateJSONFeature(self, filename, topArticleType):
        featureAr = []
        topArticles = topArticleType
        for article in topArticles:
            articleDict = article[1]
            pointTuple = (float(articleDict["x"]), float(articleDict["y"]))
            newPoint = Point(pointTuple)
            properties = {'titleLabel': articleDict["name"], 
                        'popularity': articleDict["popularity"],
                        'cluster': articleDict["cluster"]}
            newFeature = Feature(geometry=newPoint, properties=properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(filename, "w") as writeFile:
            writeFile.write(textDump)


if __name__ == "__main__":
    titleLabel = TopTitlesGeoJSONWriter(5)
    titleLabel.getTopCountryArticles()
    titleLabel.generateJSONFeature("./data/tsv/testTopCountryTitles.geojson", titleLabel.getTopCountryArticles())