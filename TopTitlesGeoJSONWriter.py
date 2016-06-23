from geojson import Feature, FeatureCollection
from geojson import dumps, Point
import Constants


#Temp fix for addition of top category labelling 

class TopTitlesGeoJSONWriter:

    def __init__(self, fileName):
        self.fileName = fileName

    def _matchPointsToTitle(self):
        nameDict = {}
        with open("./data/numberedNames.tsv") as names:
            namelines = names.readlines()
            for line in namelines:
                lineAr =line.split("\t")
                name = lineAr[1].rstrip('\n')
                idName = lineAr[0]
                nameDict[name] = idName

        idToPointDict = {}
        with open('./data/tsne_cache.tsv') as points:
            pointlines = points.readlines()
            for line in pointlines:
                lineAr = line.split("\t")
                pointTuple = (float(lineAr[1]), float(lineAr[2].rstrip('\n')))
                idToPointDict[lineAr[0]] = pointTuple

        pointList = []
        with open("./data/top_100_articles.tsv") as top100:
            allArticles = top100.readlines()
            for article in allArticles:
                name = article.split("\t")[0]
                index = nameDict[name]
                point = idToPointDict[index]
                pointList.append((name, point))

        return(pointList)


    def generateJSONFeature(self):
        featureAr = []
        for titlePt in self._matchPointsToTitle():
            newPoint = Point(titlePt[1])
            properties = {'titleLabel':titlePt[0]}
            newFeature = Feature(geometry = newPoint, properties= properties)
            featureAr.append(newFeature)
        collection = FeatureCollection(featureAr)
        textDump = dumps(collection)
        with open(self.fileName, "w") as writeFile:
            writeFile.write(textDump)