import mapnik
import luigi
import Config
import Utils
import Colors
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from PGLoader import LoadCoordinates, LoadCountries
from PGLoader import LoadContoursDensity, LoadContoursCentroid
from mapnik import register_fonts


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class CreateMapXml(MTimeMixin, luigi.Task):
    '''
    Creates the mapnik map.xml configuration file and renders png and svg
    images of the map for visual reference to make sure code excuted properly.
    Map png and svg can be found in ./data/images
    '''
    def output(self):
        config = Config.get()
        return (
            TimestampedLocalTarget(config.get("MapOutput",
                                              "map_file_density")),
            TimestampedLocalTarget(config.get("MapOutput",
                                              "map_file_centroid")))

    def requires(self):
        return (
            LoadContoursDensity(),
            LoadContoursCentroid(),
            LoadCoordinates(),
            LoadCountries(),
            MapStylerCode(),
            Colors.ColorsCode()
        )

    def generateXml(self, contourDB, contourFile, mapfile):
        config = Config.get()
        regionClusters = Utils.read_features(config.get("MapData", "clusters_with_region_id"))
        regionIds = sorted(set(int(region['cluster_id']) for region in regionClusters.values()))
        regionIds = map(str, regionIds)
        countryBorders = Utils.read_features(config.get("GeneratedFiles", "country_borders"))
        colorFactory = Colors.ColorSelector(countryBorders, Config.getColorWheel())
        colors = colorFactory.optimalColoring()

        ms = MapStyler(config, colors)
        imgfile = config.get("MapOutput", "img_src_name")

        ms.addCustomFonts(config.get("MapResources", "fontDir"))

        ms.makeMap(contourFile,
                   config.get("MapData", "countries_geojson"),
                   regionIds, contourDB)
        ms.saveMapXml(config.get("MapData", "countries_geojson"),
                      mapfile)
        ms.saveImage(mapfile, imgfile + ".png")
        ms.saveImage(mapfile, imgfile + ".svg")

    def run(self):
        config = Config.get()
        self.generateXml('contoursdensity', config.get("MapData", "density_contours_geojson"), config.get("MapOutput", "map_file_density"))

        self.generateXml('contourscentroid', config.get("MapData", "centroid_contours_geojson"), config.get("MapOutput", "map_file_centroid"))



class MapStyler:
    '''
    Creates the Wikipeida Mapnik map.
    '''

    def __init__(self, config, colorwheel):
        self.config = config
        self.numContours = config.getint("PreprocessingConstants", "num_contours")
        self.numClusters = config.getint("PreprocessingConstants", "num_clusters")
        self.colorWheel = colorwheel
        self.width = config.getint("MapConstants", "map_width")
        self.height = config.getint("MapConstants", "map_height")
        self.m = None
        d = 3000000
        self.extents = mapnik.Box2d(-d, -d, d, d)

    def addCustomFonts(self, customFontsDir):
        '''
        Picks the font that the labels are written in.
        '''
        register_fonts(customFontsDir)
        # for face in FontEngine.face_names():print face

    def makeMap(self, contourFilename, countryFilename, clusterIds, contoursDB):
        '''
        Makes the map based off of the layers that have been given to it.
        '''
        self.m = mapnik.Map(self.width, self.height)
        self.m.background = mapnik.Color('#ddf1fd')
        self.m.srs = '+init=epsg:3857'

        self.m.append_style("countries",
                            self.generateCountryPolygonStyle(countryFilename,
                                                             1.0, clusterIds))
        self.m.layers.append(self.generateLayer('countries',
                                                "countries",
                                                ["countries"]))

        styles = self.generateContourPolygonStyle(1.0, self.numContours, clusterIds)
        sNames = []
        for i, s in enumerate(styles):
            name = "contour" + str(i)
            self.m.append_style(name, s)
            sNames.append(name)
        self.m.layers.append(self.generateLayer(contoursDB, "contour", sNames))

        self.m.append_style("outline",
                            self.generateLineStyle("#000000", 1.0))
        self.m.layers.append(self.generateLayer('countries', "outline", ["outline"]))

        # extent = mapnik.Box2d(-180.0, -180.0, 90.0, 90.0)
        # print(extent)
        # self.m.zoom_to_box(self.extents)

        self.m.zoom_all()

        # print(self.m.envelope())

    def saveMapXml(self, countryFilename, mapFilename):
        assert(self.m is not None)
        mapnik.save_map(self.m, mapFilename)

    def saveImage(self, mapFilename, imgFilename):
        if self.m is None:
            self.m = mapnik.Map(self.width, self.height)
        mapnik.load_map(self.m, mapFilename)
        # extent = mapnik.Box2d(-300, -180.0, 90.0, 90.0)
        # self.m.zoom_to_box(self.extents)
        self.m.zoom_all()
        mapnik.render_to_file(self.m, imgFilename)

    def generateCountryPolygonStyle(self, filename, opacity, clusterIds):
        '''
        Creates a country polygon style.
        '''
        s = mapnik.Style()
        for i, c in enumerate(clusterIds):
            r = mapnik.Rule()
            symbolizer = mapnik.PolygonSymbolizer()
            symbolizer.fill = mapnik.Color(self.colorWheel[i][7])
            symbolizer.fill_opacity = opacity
            r.symbols.append(symbolizer)
            r.filter = mapnik.Expression('[clusternum].match("' + c + '")')
            s.rules.append(r)
        return s

    def generateContourPolygonStyle(self, opacity, numContours, clusterIds, gamma=1):
        '''
        Creates a contour polygon style by adding specific colors for
        each contour. Returns a list of styles.
        '''
        styles = []
        for i in range(self.numClusters):
            for j in range(numContours):
                s = mapnik.Style()
                r = mapnik.Rule()
                symbolizer = mapnik.PolygonSymbolizer()
                symbolizer.fill = mapnik.Color(self.colorWheel[i][j])
                symbolizer.fill_opacity = opacity
                symbolizer.gamma = gamma
                r.symbols.append(symbolizer)
                r.filter = mapnik.Expression('[identity].match("' + str(j) + str(i) + '")')
                s.rules.append(r)
                styles.append(s)
        return styles

    def generateLineStyle(self, color, opacity, dash=None):
        '''
        Creates a Line style. adn gives it back
        '''
        s = mapnik.Style()
        r = mapnik.Rule()
        symbolizer = mapnik.LineSymbolizer()
        symbolizer.stroke = mapnik.Color(color)
        symbolizer.stroke_opacity = opacity
        symbolizer.stroke_width = 2
        if dash:
            symbolizer.stroke_dasharray = dash
        r.symbols.append(symbolizer)
        s.rules.append(r)
        s.comp_op = mapnik.CompositeOp.overlay
        return s

    def generateLayer(self, tableName, name, styleNames):
        '''
        Generates the layer with its multiple styles.
        '''
        ds = self.getDatasource(tableName)
        layer = mapnik.Layer(name)
        layer.datasource = ds
        layer.cache_features = True
        for s in styleNames:
            layer.styles.append(s)
        layer.srs = '+init=epsg:4236'
        return layer

    def getDatasource(self, table):
        return mapnik.PostGIS(
            host = self.config.get('PG', 'host'),
            user = self.config.get('PG', 'user') or None,
            password = self.config.get('PG', 'password') or None,
            dbname = self.config.get('PG', 'database'),
            max_async_connection = 4,
            #estimate_extent = True,
            table = table
        )
