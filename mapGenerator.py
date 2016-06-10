import mapnik
from mapRepresentations import continentListToFile
from mapRepresentations import Continent
from borderFactory import BorderFactory
from generateTiles import renderMap


# ===== Constants ===================
IMGNAME = "./data/world"
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
        continentListToFile(featureList, fileName + str(index) + ".geoJSON")


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


def makeMap():
    m = mapnik.Map(1200, 600)
    m.background = mapnik.Color('white')

    m.append_style("0", generateStyle("#9AFFFB"))  # Good
    m.layers.append(generateLayer("./data/0.geoJSON", "0", "0"))  # Good

#    m.append_style("1", generateStyle("#9AFFDA"))
#    m.layers.append(generateLayer("./data/1.geoJSON", "1", "1"))


#    m.append_style("2", generateStyle("#9AFFFB"))
#    m.layers.append(generateLayer("./data/2.geoJSON", "2", "2"))

#    m.append_style("3", generateStyle("#FF9AF1"))
#    m.layers.append(generateLayer("./data/3.geoJSON", "3", "3"))

    m.append_style("4", generateStyle("#FFA79A"))  # Good
    m.layers.append(generateLayer("./data/4.geoJSON", "4", "4"))  # Good

#    m.append_style("5", generateStyle("#CCCCCC"))  # Maybe?
#    m.layers.append(generateLayer("./data/5.geoJSON", "5", "5"))  # Maybe?

    m.append_style("6", generateStyle("#DA9AFF"))  # Good
    m.layers.append(generateLayer("./data/6.geoJSON", "6", "6"))  # Good

#    m.append_style("7", generateStyle("#FFDA9A"))  # Maybe?
#    m.layers.append(generateLayer("./data/7.geoJSON", "7", "7"))  # Maybe?

    m.append_style("8", generateStyle("#FFD7B1"))  # Good
    m.layers.append(generateLayer("./data/8.geoJSON", "8", "8"))  # Good

    m.append_style("9", generateStyle("#FF9ABE"))  # Good
    m.layers.append(generateLayer("./data/9.geoJSON", "9", "9"))  # Good

    m.zoom_all()

    mapnik.save_map(m, "map.xml")
    mapnik.render_to_file(m, IMGNAME + ".png")
    mapnik.render_to_file(m, IMGNAME + ".svg")
    print "rendered image to", IMGNAME

generatePolygonFile()
makeMap()
renderMap()
