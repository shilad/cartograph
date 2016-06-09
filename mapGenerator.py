import mapnik
from math import cos, sin
from random import uniform, seed
from mapRepresentations import continentListToFile
from mapRepresentations import Continent


# ===== Constants ===================
SEED_DISTANCE = .001
IMGNAME = "./data/world.png"
WATER_DATA = "./data/water.json"
LAND_DATA = "./data/earth.json"
POINT_DATA = "./data/data.csv"


# ===== Generate JSON Data ==========
def findCoordinate(centerPt, dist, theta=0):
        lon = centerPt[0] + (dist * cos(theta))
        lat = centerPt[1] + (dist * sin(theta))
        return (lat, lon)


def genPt(maxDist=SEED_DISTANCE):
    seed()
    return (uniform(0, maxDist), uniform(0, maxDist))


def generatePolygonFile():
    with open(POINT_DATA, 'rb') as dataFile:
        linesOfInterest = dataFile.readlines()[:10]

    linesOfInterest = [line.split(",") for line in linesOfInterest[1:]]
    points = [(float(line[1]), float(line[2])) for line in linesOfInterest]
    continents = [Continent(point) for point in points]
    waterFeaturesList = []
    landFeaturesList = []

    for continent in continents:
        for num in range(6):
            continent.addEdge(genPt(), genPt())

    for index, continent in enumerate(continents):
        if index % 2 == 0:
            waterFeaturesList.append(continent)
        else:
            landFeaturesList.append(continent)

    continentListToFile(landFeaturesList, LAND_DATA)
    continentListToFile(waterFeaturesList, WATER_DATA)


# ===== Generate Map File =====
def makeMap(earthFile, waterFile):
    m = mapnik.Map(600, 300)
    m.background = mapnik.Color('white')

    s = mapnik.Style()
    r = mapnik.Rule()
    s2 = mapnik.Style()
    r2 = mapnik.Rule()

    polygon_symbolizer2 = mapnik.PolygonSymbolizer()
    polygon_symbolizer2.fill = mapnik.Color(20, 60, 200, 100)
    r2.symbols.append(polygon_symbolizer2)
    s2.rules.append(r2)
    m.append_style("Water", s2)

    polygon_symbolizer = mapnik.PolygonSymbolizer()
    polygon_symbolizer.fill = mapnik.Color(60, 200, 100, 100)
    line_symbolizer = mapnik.LineSymbolizer()
    r.symbols.append(polygon_symbolizer)
    r.symbols.append(line_symbolizer)
    s.rules.append(r)
    m.append_style('Earth', s)

    ds = mapnik.GeoJSON(file=earthFile)
    layer = mapnik.Layer('earth')
    layer.datasource = ds
    layer.styles.append('Earth')

    ds2 = mapnik.GeoJSON(file=waterFile)
    layer2 = mapnik.Layer("water")
    layer2.datasource = ds2
    layer2.styles.append("Water")

    m.layers.append(layer)
    m.layers.append(layer2)
    m.zoom_all()

    mapnik.render_to_file(m, IMGNAME, 'png')
    print "rendered image to", IMGNAME

generatePolygonFile()
makeMap(LAND_DATA, WATER_DATA)
