import mapnik
from mapRepresentations import continentListToFile
from mapRepresentations import Continent
from borderFactory import BorderFactory


# ===== Constants ===================
IMGNAME = "./data/world"
WATER_DATA = "./data/water.json"
LAND_DATA = "./data/earth.json"
POINT_DATA = "./data/data.csv"


# ===== Generate JSON Data ==========
def generateFeatureList(pointList):
    newList = []
    for region in pointList:
        newContinent = Continent((0, 0))
        for point in region:
            newContinent.addPoint(point)
        newList.append(newContinent)
    return newList


def generatePolygonFile():
    clusterList = BorderFactory(POINT_DATA).build().values()
    fileName = "./data/"
    for index, cluster in enumerate(clusterList):
        featureList = generateFeatureList(cluster)
        continentListToFile(featureList, fileName + str(index) + ".json")


# ===== Generate Map File =====
def generateStyle(color):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.PolygonSymbolizer()
    symbolizer.fill = mapnik.Color(color)
    r.symbols.append(symbolizer)
    s.rules.append(r)
    return s


def generateLayer(jsonFile, name, styleName):
    ds = mapnik.GeoJSON(file=jsonFile)
    layer = mapnik.Layer(name)
    layer.datasource = ds
    layer.styles.append(styleName)
    return layer


def makeMap(earthFile, waterFile):
    m = mapnik.Map(600, 300)
    m.background = mapnik.Color('white')

    m.append_style("0", generateStyle("#9AFFFB"))  # Good
    m.layers.append(generateLayer("./data/0.json", "0", "0"))  # Good

#    m.append_style("1", generateStyle("#9AFFDA"))
#    m.layers.append(generateLayer("./data/1.json", "1", "1"))


#    m.append_style("2", generateStyle("#9AFFFB"))
#    m.layers.append(generateLayer("./data/2.json", "2", "2"))

#    m.append_style("3", generateStyle("#FF9AF1"))
#    m.layers.append(generateLayer("./data/3.json", "3", "3"))

    m.append_style("4", generateStyle("#FFA79A"))  # Good
    m.layers.append(generateLayer("./data/4.json", "4", "4"))  # Good

#    m.append_style("5", generateStyle("#CCCCCC"))  # Maybe?
#    m.layers.append(generateLayer("./data/5.json", "5", "5"))  # Maybe?

    m.append_style("6", generateStyle("#DA9AFF"))  # Good
    m.layers.append(generateLayer("./data/6.json", "6", "6"))  # Good

#    m.append_style("7", generateStyle("#FFDA9A"))  # Maybe?
#    m.layers.append(generateLayer("./data/7.json", "7", "7"))  # Maybe?

    m.append_style("8", generateStyle("#FFD7B1"))  # Good
    m.layers.append(generateLayer("./data/8.json", "8", "8"))  # Good

    m.append_style("9", generateStyle("#FF9ABE"))  # Good
    m.layers.append(generateLayer("./data/9.json", "9", "9"))  # Good

    m.zoom_all()

    mapnik.save_map(m, "./data/map.xml")
    mapnik.render_to_file(m, IMGNAME + ".png")
    mapnik.render_to_file(m, IMGNAME + ".svg")
    print "rendered image to", IMGNAME

generatePolygonFile()
makeMap(LAND_DATA, WATER_DATA)
