import Utils
import luigi
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from geojson import Feature, FeatureCollection
from geojson import dumps, Point


class TopTitlesGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class TopTitlesGeoJSONWriter:
    def __init__(self, numArticles, featureDict, numClusters):
        self.numArticles = numArticles
        self.articleData = featureDict
        self.numClusters = numClusters

    def getTopCountryArticles(self):
        sortedByClust = [[] for i in range(self.numClusters)]
        articleDict = self.articleData
        topCountryArticles = []
        for key in articleDict:
            c = int(articleDict[key]['cluster'])
            sortedByClust[c].append((key, articleDict[key]))
        for clustArticles in sortedByClust:
            clustArticles.sort(key=lambda x: (x[1]['popularity']),
                               reverse=True)
            topCountryArticles = topCountryArticles + clustArticles[:self.numArticles]
        return(topCountryArticles)

    def getTopArticles(self):
        allArticles = Utils.sort_by_feature(self.articleData, "popularity")
        return allArticles[:self.numArticles]

    def generateTopJSONFeature(self, filename):
        featureAr = []
        topArticles = self.getTopArticles()
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
    titleLabel.generateJSONFeature("./data/tsv/testTopCountryTitles.geojson",
                                   titleLabel.getTopCountryArticles())
