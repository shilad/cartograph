import mapnik
from MapRepresentations import continentListToFile
from MapRepresentations import Continent
from borderFactory import BorderFactory
from histToContour import Contours
from geojson import Feature, FeatureCollection, dumps, Polygon
from generateTiles import render_tiles
from addLabelsXml import writeLabelsXml

# ===== Constants ===================
IMGNAME = "./data/world"
POINT_DATA = "./data/data.csv"
CONTOUR_DATA = "contourData.geojson"
fullFeatureList = []


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
        fullFeatureList.append(featureList)
        
    continentListToFile(fullFeatureList, fileName + "countries.geoJSON")


# ===== Generate Map File =====
def generateCountryPolygonStyle(filename, opacity):
    colorWheel = ["#9AFFFC", "#9AFFDA", "#9AFFFB", "#FF9AF1", "#FFA79A", "#CCCCCC", "#DA9AFF", "#FFDA9A", "#FFD7B1", "#FF9ABE"]
    s = mapnik.Style()
    for i in range(len(fullFeatureList)):
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color(colorWheel[i])
        symbolizer.fill_opacity = opacity
        r.symbols.append(symbolizer)
        r.filter = mapnik.Filter('[clusterNum].match("'+ str(i) + '")')
        s.rules.append(r)

    return s

def generateSinglePolygonStyle(filename, opacity, color):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.PolygonSymbolizer()
    symbolizer.fill = mapnik.Color('steelblue')
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

    m.append_style("countries", generateCountryPolygonStyle("./data/countries.geoJSON", 1.0))
    m.layers.append(generateLayer("./data/countries.geoJSON", "countries", "countries"))

# ======== Make Contour Layer =========
    m.append_style("contour", generateSinglePolygonStyle("contourData.geojson", .20, 1))
    m.layers.append(generateLayer("contourData.geojson",
                                  "contour", "contour"))

    m.append_style("outline", generateLineStyle("darkblue", 1.0))
    m.layers.append(generateLayer("contourData.geojson",
                                  "outline", "outline"))

    m.zoom_all()

    mapnik.save_map(m, "map.xml")

    writeLabelsXml('[labels]', 'polygon','./data/countries.geojson')

    mapnik.render_to_file(m, IMGNAME + ".png")
    mapnik.render_to_file(m, IMGNAME + ".svg")
    print "rendered image to", IMGNAME

if __name__ == "__main__":
    generatePolygonFile()
    contour = Contours('./data/data.csv', "contourData.geojson")
    contour.makeContourFeatureCollection()
    makeMap()

    mapfile = "map.xml"
    tile_dir = "tiles/"
    bbox = (-180.0, -90.0, 180.0, 90.0)
    render_tiles(bbox, mapfile, tile_dir, 0, 5, "World")
