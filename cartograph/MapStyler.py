from json import load
from geojson import dumps
import mapnik
import Labels
import Config
from shapely.geometry import shape, mapping
config = Config.BAD_GET_CONFIG()


class MapStyler:
    def __init__(self, width=800, height=600):
        self.m = None
        self.width = width
        self.height = height

    def makeMap(self, contourFilename, countryFilename, clusterIds):
        self.m = mapnik.Map(self.width, self.height)
        self.m.background = mapnik.Color('white')
        self.m.srs = '+init=epsg:3857'

        jsContour = load(open(contourFilename, 'r'))
        numContours = [0 for x in range(config.NUM_CLUSTERS)]
        for feat in jsContour['features']:
            numContours[feat['properties']['clusterNum']] += 1

        self.m.append_style("countries", generateCountryPolygonStyle(countryFilename, .35, clusterIds))
        self.m.layers.append(generateLayer(countryFilename, "countries", "countries"))

        self.m.append_style("contour", generateContourPolygonStyle(.20, numContours))
        self.m.layers.append(generateLayer(contourFilename, "contour", "contour"))

        self.m.append_style("outline", generateLineStyle("#999999", 1.0, '3,3'))
        self.m.layers.append(generateLayer(countryFilename, "outline", "outline"))
        self.m.zoom_all()

    def saveMapXml(self, countryFilename, mapFilename):
        assert(self.m is not None)
        mapnik.save_map(self.m, mapFilename)

    def saveImage(self, mapFilename, imgFilename):
        if self.m is None:
            self.m = mapnik.Map(self.width, self.height)
        mapnik.load_map(self.m, mapFilename)
        self.m.zoom_all()
        mapnik.render_to_file(self.m, imgFilename)


"""
TODO: move the functions below into the above class
"""


def generateSinglePolygonStyle(filename, opacity, color, gamma=1):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.PolygonSymbolizer()
    symbolizer.fill = mapnik.Color('steelblue')
    symbolizer.fill_opacity = opacity
    symbolizer.gamma = gamma
    r.symbols.append(symbolizer)
    s.rules.append(r)
    return s


# ===== Generate Map File =====
def generateCountryPolygonStyle(filename, opacity, clusterIds):
    colorWheel = ["#ff86d3", "#79dc6d","#b346f8","#f1bc00","#03018c",
                  "#b7d15c", "#3e89ff","#ff8200","#003580","#ec0035",
                  "#00853f", "#bd002d","#01828c","#73001a","#8f9dff",
                  "#853e00", "#b5c1ff","#510032","#c6c999","#0074aa",
                  "#f9b3c9", "#006042"]
    s = mapnik.Style()
    for i, c in enumerate(clusterIds):
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color(colorWheel[i])
        symbolizer.fill_opacity = opacity
        r.symbols.append(symbolizer)
        r.filter = mapnik.Expression('[clusterNum].match("' + c + '")')
        s.rules.append(r)
    return s


def generateContourPolygonStyle(opacity, numContours, gamma=1):
    colorWheel = ["#ff86d3", "#79dc6d","#b346f8","#f1bc00","#03018c",
                  "#b7d15c", "#3e89ff","#ff8200","#003580","#ec0035",
                  "#00853f", "#bd002d","#01828c","#73001a","#8f9dff",
                  "#853e00", "#b5c1ff","#510032","#c6c999","#0074aa",
                  "#f9b3c9", "#006042"]
    testColors = ["#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF",
                  "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF",
                  "#FFFFFF", "#FFFFFF", "#FFFFFF", "#673AB7"]
    s = mapnik.Style()
    for i in range(config.NUM_CLUSTERS):
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color(colorWheel[i])
        symbolizer.fill_opacity = opacity
        symbolizer.gamma = gamma
        r.symbols.append(symbolizer)
        r.filter = mapnik.Expression('[clusterNum].match("' + str(i) + '")')
        s.rules.append(r)
    return s


def generateLineStyle(color, opacity, dash=None):
    s = mapnik.Style()
    r = mapnik.Rule()
    symbolizer = mapnik.LineSymbolizer()
    symbolizer.stroke = mapnik.Color(color)
    symbolizer.stroke_opacity = opacity
    if dash:
        symbolizer.stroke_dasharray = dash
    r.symbols.append(symbolizer)
    s.rules.append(r)
    return s


def generateLayer(jsonFile, name, styleName):
    ds = mapnik.GeoJSON(file=jsonFile)
    layer = mapnik.Layer(name)
    layer.datasource = ds
    layer.styles.append(styleName)
    layer.srs = '+init=epsg:4236'
    return layer
