import mapnik
from MapRepresentations import continentListToFile
from MapRepresentations import Continent
from borderFactory import BorderFactory
from histToContour import getContours
from geojson import Feature, FeatureCollection, dumps, Polygon
from generateTiles import render_tiles
from addLabelsXml import writeLabelsXml

# ===== Constants ===================
IMGNAME = "./data/world"
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
    clusterList = BorderFactory.from_file(POINT_DATA).build().values()
    fileName = "./data/"
    for index, cluster in enumerate(clusterList):
        featureList = generateFeatureList(cluster)
        continentListToFile(featureList, fileName + str(index) + ".geoJSON")


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


def generateLineStyle(color, opacity):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.LineSymbolizer()
    symbolizer.stroke = mapnik.Color(color)
    symbolizer.stroke_opacity = opacity
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

    m.append_style("0", generatePolygonStyle("#9AFFFB", 1.0))  # Good
    m.layers.append(generateLayer("./data/0.geoJSON", "0", "0"))  # Good

    m.append_style("1", generatePolygonStyle("#9AFFDA", 1.0))
    m.layers.append(generateLayer("./data/1.geoJSON", "1", "1"))

    m.append_style("2", generatePolygonStyle("#9AFFFB", 1.0))
    m.layers.append(generateLayer("./data/2.geoJSON", "2", "2"))

    m.append_style("3", generatePolygonStyle("#FF9AF1", 1.0))
    m.layers.append(generateLayer("./data/3.geoJSON", "3", "3"))

    m.append_style("4", generatePolygonStyle("#FFA79A", 1.0))  # Good
    m.layers.append(generateLayer("./data/4.geoJSON", "4", "4"))  # Good

    m.append_style("5", generatePolygonStyle("#CCCCCC", 1.0))  # Maybe?
    m.layers.append(generateLayer("./data/5.geoJSON", "5", "5"))  # Maybe?

    m.append_style("6", generatePolygonStyle("#DA9AFF", 1.0))  # Good
    m.layers.append(generateLayer("./data/6.geoJSON", "6", "6"))  # Good

    m.append_style("7", generatePolygonStyle("#FFDA9A", 1.0))  # Maybe?
    m.layers.append(generateLayer("./data/7.geoJSON", "7", "7"))  # Maybe?

    m.append_style("8", generatePolygonStyle("#FFD7B1", 1.0))  # Good
    m.layers.append(generateLayer("./data/8.geoJSON", "8", "8"))  # Good

    m.append_style("9", generatePolygonStyle("#FF9ABE", 1.0))  # Good
    m.layers.append(generateLayer("./data/9.geoJSON", "9", "9"))  # Good

# ======== Make Contour Layer =========
    m.append_style("contour", generatePolygonStyle("steelblue", .30))
    m.layers.append(generateLayer("simpleWikiMapData.geojson",
                                  "contour", "contour"))

    m.append_style("outline", generateLineStyle("darkblue", 1.0))
    m.layers.append(generateLayer("simpleWikiMapData.geojson",
                                  "outline", "outline"))

    m.zoom_all()

    mapnik.save_map(m, "map.xml")

    #writeLabelsXml('[labels]', 'polygon','countries.geojson')

    mapnik.render_to_file(m, IMGNAME + ".png")
    mapnik.render_to_file(m, IMGNAME + ".svg")
    print "rendered image to", IMGNAME

if __name__ == "__main__":
    generatePolygonFile()
    makeContourFeatureCollection(getContours())
    makeMap()

    mapfile = "map.xml"
    tile_dir = "tiles/"
    bbox = (-180.0, -90.0, 180.0, 90.0)
    render_tiles(bbox, mapfile, tile_dir, 0, 5, "World")
