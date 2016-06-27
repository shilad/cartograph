import json
import mapnik
import Labels
from shapely.geometry import mapping, shape
import Config
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

        js = json.load(open(contourFilename, 'r'))
        numContours = [0 for x in range(config.NUM_CLUSTERS)]
        for i in range(len(js['features'])):
            numContours[js['features'][i]['properties']['clusterNum']] += 1

        self.m.append_style("countries", generateCountryPolygonStyle(countryFilename, .20, clusterIds))
        self.m.layers.append(generateLayer(countryFilename, "countries", "countries"))

        self.m.append_style("contour", generateContourPolygonStyle(.15, numContours))
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
    colorWheel = ["#795548", "#FF5722", "#FFC107", "#CDDC39", "#4CAF50", "#009688", "#00BCD4", "#2196F3", "#3F51B5", "#673AB7"]
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
    colorWheel = ["#795548", "#FF5722", "#FFC107", "#CDDC39", "#4CAF50", "#009688", "#00BCD4", "#2196F3", "#3F51B5", "#673AB7"]
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
