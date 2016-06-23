from MapRepresentations import Continent, continentListToFile
import BorderFactory


class ContinentFactory:
    fullFeatureList = []

    def __init__(self, countriesFile):
        self.countriesFile = countriesFile

    # ===== Generate JSON Data ==========
    def _generateFeatureList(self, pointList):
        newList = []
        for region in pointList:
            newContinent = Continent((0, 0))
            for point in region:
                newContinent.addPoint(point)
            newList.append(newContinent)
        return newList

    def generatePolygonFile(self):
        clusterList = BorderFactory.from_file().build().values()
        for index, cluster in enumerate(clusterList):
            print "Generating cluster", index
            featureList = self._generateFeatureList(cluster)
            self.fullFeatureList.append(featureList)

        continentListToFile(self.fullFeatureList, self.countriesFile)
