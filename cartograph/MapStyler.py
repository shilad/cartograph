import mapnik
from mapnik import register_fonts, FontEngine


class MapStyler:



    def __init__(self, config, colorwheel):
        self.config = config
        self.numContours =  config.getint("PreprocessingConstants", "num_contours")
        self.numClusters = config.getint("PreprocessingConstants", "num_clusters")
        self.colorWheel = colorwheel
        self.width = config.getint("MapConstants", "map_width")
        self.height = config.getint("MapConstants", "map_height")
        self.m = None
        d = 3000000
        self.extents = mapnik.Box2d(-d, -d, d, d)

    def addCustomFonts(self, customFontsDir):
        register_fonts(customFontsDir)
        # for face in FontEngine.face_names():print face

    def makeMap(self, contourFilename, countryFilename, clusterIds, contoursDB):
        self.m = mapnik.Map(self.width, self.height)
        self.m.background = mapnik.Color('#ddf1fd')
        self.m.srs = '+init=epsg:3857'


        self.m.append_style("countries",
                            self.generateCountryPolygonStyle(countryFilename,
                                                             1.0, clusterIds))
        self.m.layers.append(self.generateLayer('countries', "countries", ["countries"]))

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
        #extent = mapnik.Box2d(-300, -180.0, 90.0, 90.0)
        #self.m.zoom_to_box(self.extents)
        self.m.zoom_all()
        mapnik.render_to_file(self.m, imgFilename)

    def generateSinglePolygonStyle(self, filename, opacity, color, gamma=1):
        s = mapnik.Style()
        r = mapnik.Rule()
        symbolizer = mapnik.PolygonSymbolizer()
        symbolizer.fill = mapnik.Color('steelblue')
        symbolizer.fill_opacity = opacity
        symbolizer.gamma = gamma
        r.symbols.append(symbolizer)
        s.rules.append(r)
        return s

    def generateCountryPolygonStyle(self, filename, opacity, clusterIds):
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
        s = mapnik.Style()
        r = mapnik.Rule()
        symbolizer = mapnik.LineSymbolizer()
        symbolizer.stroke = mapnik.Color(color)
        symbolizer.stroke_opacity = opacity
        symbolizer.stroke_width = 1.5
        if dash:
            symbolizer.stroke_dasharray = dash
        r.symbols.append(symbolizer)
        s.rules.append(r)
        s.comp_op = mapnik.CompositeOp.overlay
        return s

    def generateLayer(self, tableName, name, styleNames):
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