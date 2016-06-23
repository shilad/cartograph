import mapnik
from cartograph.BorderGeoJSONWriter import BorderGeoJSONWriter
from cartograph.BorderFactory import BorderFactory
from cartograph.Contours import ContourCreator
from shutil import rmtree
from cartograph.Labels import Labels
import cartograph.Config
from cartograph.TopTitlesGeoJSONWriter import TopTitlesGeoJSONWriter

fullFeatureList = []
numOfContours = 0

config = cartograph.Config.BAD_GET_CONFIG()


# ===== Generate JSON Data ==========
def generateCountryFile():
    clusterList = BorderFactory.from_file().build().values()
    BorderGeoJSONWriter(clusterList).writeToFile(config.FILE_NAME_COUNTRIES)
    global fullFeatureList
    fullFeatureList = clusterList


def generateTitleLabelFile():
    titleLabels = TopTitlesGeoJSONWriter(100)
    titleLabels.generateJSONFeature(config.FILE_NAME_TOP_TITLES)


def generateContourFile():
    contour = ContourCreator(config.FILE_NAME_COORDS_AND_CLUSTERS)
    contour.makeContourFeatureCollection()
    global numOfContours
    numOfContours = len(contour.plys)


# ===== Generate Map File =====
def generateCountryPolygonStyle(opacity):
    colorWheel = ["#795548", "#FF5722", "#FFC107", "#CDDC39", "#4CAF50", "#009688", "#00BCD4", "#2196F3", "#3F51B5", "#673AB7"]
    s = mapnik.Style()
    for i in range(len(fullFeatureList)):
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color(colorWheel[i])
        symbolizer.fill_opacity = opacity
        r.symbols.append(symbolizer)
        r.filter = mapnik.Expression('[clusterNum].match("' + str(i) + '")')
        s.rules.append(r)
    return s


def generateContourPolygonStyle(opacity, gamma=1):
    colorWheel = ["#d2b8e3 ", "#b2cefe", "#baed91", "#faf884", "#f8b88b", "#fd717b", "red"]
    s = mapnik.Style()
    for i in range(numOfContours):
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color(colorWheel[i])
        symbolizer.fill_opacity = opacity
        symbolizer.gamma = gamma
        r.symbols.append(symbolizer)
        r.filter = mapnik.Expression('[contourNum].match("' + str(i) + '")')
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
    layer.srs = '+init=epsg:4236'
    return layer


def makeMap():
    m = mapnik.Map(1000, 1000)
    m.background = mapnik.Color('white')
    m.srs = '+init=epsg:3857'


# ======== Make Contour Layer =========
    m.append_style("contour", generateContourPolygonStyle(.3))
    m.layers.append(generateLayer(config.FILE_NAME_CONTOUR_DATA,
                                  "contour", "contour"))

    m.append_style("outline", generateLineStyle("black", 0.0))
    m.layers.append(generateLayer(config.FILE_NAME_CONTOUR_DATA,
                                  "outline", "outline"))

    m.append_style("countries", generateCountryPolygonStyle(.3))
    m.layers.append(generateLayer(config.FILE_NAME_COUNTRIES, "countries", "countries"))
    m.zoom_all()

    mapnik.save_map(m, config.FILE_NAME_MAP)

    label = Labels()
    label.writeLabelsXml('[labels]', 'interior', config.FILE_NAME_COUNTRIES, maxScale='559082264', minScale='17471321')

    titleLabels = Labels()
    titleLabels.writeLabelsXml('[titleLabel]', 'point', config.FILE_NAME_TOPTITLES, minScale='1091958', maxScale='17471321')

    mapnik.load_map(m, config.FILE_NAME_MAP)

    mapnik.render_to_file(m, config.FILE_NAME_IMGNAME + ".png")
    mapnik.render_to_file(m, config.FILE_NAME_IMGNAME + ".svg")
    print "rendered image to", config.FILE_NAME_IMGNAME

if __name__ == "__main__":
    print "Generating Polygons"
    generateCountryFile()

    print "Generating TitleLabels"
    generateTitleLabelFile()

    print "Generating Contours"
    generateContourFile()

    print "Making Map XML"
    makeMap()

    mapfile = config.FILE_NAME_MAP
    tile_dir = config.DIRECTORY_NAME_TILES

    bbox = (-180.0, -90.0, 180.0, 90.0)
    rmtree(tile_dir)
    # render_tiles(bbox, mapfile, tile_dir, 0, 2, "World")
