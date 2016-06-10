import mapnik
from MapRepresentations import continentListToFile
from MapRepresentations import Continent
from borderFactory import BorderFactory
from histToContour import getContours
from geojson import Feature, FeatureCollection, dumps, Polygon


# ===== Constants ===================
IMGNAME = "./data/world"
WATER_DATA = "./data/water.json"
LAND_DATA = "./data/earth.json"
POINT_DATA = "./data/data.csv"
CONTOUR_DATA = "simpleWikiMapData.geojson"


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


# ===== Generate geoJSON Contour Data ========
def genContourFeatures(nmpy):
    featureAr = []
    polyGroups = []
    for group in nmpy:
        polys = []
        for shape in group:
            polyPoints = []
            for pt in shape:
                polyPoints.append((pt[0], pt[1]))
            polys.append(polyPoints)
        polyGroups.append(polys)
    for shape in polyGroups:
        newPolygon = Polygon(shape)
        newFeature = Feature(geometry=newPolygon)
        featureAr.append(newFeature)

    return featureAr


def makeContourFeatureCollection(nmpy):
    featureAr = genContourFeatures(nmpy)
    collection = FeatureCollection(featureAr)
    textDump = dumps(collection)
    with open("simpleWikiMapData.geojson", "w") as writeFile:
        writeFile.write(textDump)


# ===== Generate Map File =====
def generatePolygonStyle(color, opacity):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.PolygonSymbolizer()
    symbolizer.fill = mapnik.Color(color)
    symbolizer.fill_opacity = opacity
    r.symbols.append(symbolizer)
    s.rules.append(r)
    return s


def generateLineStyle(color):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.LineSymbolizer()
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


def makeMap(earthFile, waterFile, contourFile):
    m = mapnik.Map(600, 300)
    m.background = mapnik.Color('white')

    m.append_style("0", generatePolygonStyle("#9AFFFB", 1.0))  # Good
    m.layers.append(generateLayer("./data/0.json", "0", "0"))  # Good

#    m.append_style("1", generateStyle("#9AFFDA", 1.0))
#    m.layers.append(generateLayer("./data/1.json", "1", "1"))


#    m.append_style("2", generateStyle("#9AFFFB", 1.0))
#    m.layers.append(generateLayer("./data/2.json", "2", "2"))

#    m.append_style("3", generateStyle("#FF9AF1", 1.0))
#    m.layers.append(generateLayer("./data/3.json", "3", "3"))

    m.append_style("4", generatePolygonStyle("#FFA79A", 1.0))  # Good
    m.layers.append(generateLayer("./data/4.json", "4", "4"))  # Good

#    m.append_style("5", generateStyle("#CCCCCC", 1.0))  # Maybe?
#    m.layers.append(generateLayer("./data/5.json", "5", "5"))  # Maybe?

    m.append_style("6", generatePolygonStyle("#DA9AFF", 1.0))  # Good
    m.layers.append(generateLayer("./data/6.json", "6", "6"))  # Good

#    m.append_style("7", generateStyle("#FFDA9A", 1.0))  # Maybe?
#    m.layers.append(generateLayer("./data/7.json", "7", "7"))  # Maybe?

    m.append_style("8", generatePolygonStyle("#FFD7B1", 1.0))  # Good
    m.layers.append(generateLayer("./data/8.json", "8", "8"))  # Good

    m.append_style("9", generatePolygonStyle("#FF9ABE", 1.0))  # Good
    m.layers.append(generateLayer("./data/9.json", "9", "9"))  # Good

# ======== Make Contour Layer =========
    m.append_style("contour", generatePolygonStyle("steelblue", .30))
    m.layers.append(generateLayer("simpleWikiMapData.geojson", "contour", "contour"))

    m.append_style("outline", generateLineStyle("darkblue"))
    m.layers.append(generateLayer("simpleWikiMapData.geojson", "outline", "outline"))

    m.zoom_all()

    mapnik.save_map(m, "./data/map.xml")
    mapnik.render_to_file(m, IMGNAME + ".png")
    mapnik.render_to_file(m, IMGNAME + ".svg")
    print "rendered image to", IMGNAME

generatePolygonFile()
makeContourFeatureCollection(getContours())
makeMap(LAND_DATA, WATER_DATA, CONTOUR_DATA)
