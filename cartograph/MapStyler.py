import mapnik
import Labels

class MapStyler:
    def __init__(self):
        self.m = None

    def makeMap(self, contourFilename, countryFilename, clusterIds, width=1200, height=600):
        self.m = mapnik.Map(width, height)
        self.m.background = mapnik.Color('white')
 
        self.m.append_style("contour", generateSinglePolygonStyle(contourFilename, 0.2, 1))
        self.m.layers.append(generateLayer(contourFilename, "contour", "contour"))
 
        self.m.append_style("outline", generateLineStyle("darkblue", 0.5))
        self.m.layers.append(generateLayer(contourFilename, "outline", "outline"))
 
        self.m.append_style("countries", generateCountryPolygonStyle(countryFilename, 1.0, clusterIds))
        self.m.layers.append(generateLayer(countryFilename, "countries", "countries"))
        self.m.zoom_all()

    def saveMapXml(self, countryFilename, mapFilename):
        assert(self.m != None)
        mapnik.save_map(self.m, mapFilename)
        label = Labels.Labels(mapFilename)
        label.writeLabelsXml('[labels]', 'interior', countryFilename, mapFilename)

    def saveImage(self, mapFilename, imgFilename):
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
