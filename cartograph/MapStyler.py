from json import load
import mapnik
import Config
config = Config.BAD_GET_CONFIG()


class MapStyler:
    def __init__(self, width=800, height=600):
        self.m = None
        self.width = width
        self.height = height

        d = 3000000
        self.extents = mapnik.Box2d(-d, -d, d, d)

    def makeMap(self, contourFilename, countryFilename, clusterIds):
        self.m = mapnik.Map(self.width, self.height)
        self.m.background = mapnik.Color('white')
        self.m.srs = '+init=epsg:3857'

        jsContour = load(open(contourFilename, 'r'))
        numContours = [0 for x in range(config.NUM_CLUSTERS)]
        for feat in jsContour['features']:
            numContours[feat['properties']['clusterNum']] += 1

        self.m.append_style("countries", generateCountryPolygonStyle(countryFilename, .05, clusterIds))
        self.m.layers.append(generateLayer(countryFilename, "countries", "countries"))

        self.m.append_style("contour", generateContourPolygonStyle(.20, numContours, clusterIds))
        self.m.layers.append(generateLayer(contourFilename, "contour", "contour"))

        self.m.append_style("outline", generateLineStyle("#999999", 1.0, '3,3'))
        self.m.layers.append(generateLayer(countryFilename, "outline", "outline"))

        #extent = mapnik.Box2d(-180.0, -180.0, 90.0, 90.0)
        #print(extent)
        #self.m.zoom_to_box(self.extents)
        self.m.zoom_all()
        #print(self.m.envelope())

    def saveMapXml(self, countryFilename, mapFilename):
        assert(self.m is not None)
        mapnik.save_map(self.m, mapFilename)

    def saveImage(self, mapFilename, imgFilename):
        if self.m is None:
            self.m = mapnik.Map(self.width, self.height)
        mapnik.load_map(self.m, mapFilename)
        #extent = mapnik.Box2d(-300, -180.0, 90.0, 90.0)
        #self.m.zoom_to_box(self.extents)
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
    colorWheel = config.COLORWHEEL
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


def generateContourPolygonStyle(opacity, numContours, clusterIds, gamma=1):
    colorWheel = config.COLORWHEEL
    s = mapnik.Style()
    for i, c in enumerate(clusterIds):
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color(colorWheel[i])
        symbolizer.fill_opacity = opacity
        symbolizer.gamma = gamma
        r.symbols.append(symbolizer)
        r.filter = mapnik.Expression('[clusterNum].match("' + c + '")')
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
