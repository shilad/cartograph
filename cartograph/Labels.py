
import Config
import Utils
import luigi
from ZoomGeoJSONWriter import CreateLabelsFromZoom
from BorderGeoJSONWriter import CreateContinents
from MapStyler import CreateMapXml
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
import lxml.etree as letree
from xml.etree.ElementTree import parse, SubElement


class LabelsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class LabelMapUsingZoom(MTimeMixin, luigi.Task):
    '''
    Adding the labels directly into the xml file for map rendering.
    Labels are added to appear based on a grid based zoom calculation in
    the CalculateZooms.py
    '''
    def output(self):
        config = Config.get()
        return (
            TimestampedLocalTarget(config.get("MapOutput",
                                              "map_file_density")),
            TimestampedLocalTarget(config.get("MapOutput",
                                              "map_file_centroid")))

    def requires(self):
        return (CreateMapXml(),
                CreateLabelsFromZoom(),
                CreateContinents(),
                LabelsCode()
                )

    def generateLabels(self, contourFile, mapFile):
        config = Config.get()
        zoomScaleData = Utils.read_zoom(config.get("MapData",
                                                   "scale_dimensions"))

        labelClust = Labels(config, mapFile,
                            'countries', zoomScaleData)
        labelClust.addCustomFonts(config.get('MapResources', 'fontDir'))

        # For testing remove later.
        labelClust.embossContinents()

        labelClust.writeLabelsXml('[labels]', 'interior',
                                  breakZoom=config.getint('MapConstants', 'first_zoom_label'),
                                  minScale=10,
                                  maxScale=0)

        labelCities = Labels(config, mapFile,
                             'coordinates', zoomScaleData)
        labelCities.writeLabelsByZoomToXml('[citylabel]', 'point',
                                           config.getint("MapConstants", "max_zoom"),
                                           imgFile=config.get("MapResources", "img_dot"),
                                           numBins=config.getint("MapConstants", "num_pop_bins"))

    def run(self):
        config = Config.get()
        self.generateLabels(config.get("MapData", "density_contours_geojson"),
                            config.get("MapOutput", "map_file_density"))
        self.generateLabels(config.get("MapData", "centroid_contours_geojson"),
                            config.get("MapOutput", "map_file_centroid"))

class Labels():
    def __init__(self, config, mapfile, table, scaleDimensions):
        self.config = config
        self.mapFileName = mapfile
        self.mapFile = parse(mapfile)
        self.table = table
        self.mapRoot = self.mapFile.getroot()
        self.zoomScaleData = scaleDimensions

    def addCustomFonts(self, fontDir):
        '''
        Links the custom font directory to the xml.
        '''
        self.mapRoot.set('font-directory', fontDir)

    def getMaxDenominator(self, zoomNum):
        '''
        Returns the denominator for the maximum zoom at given zoom level.
        This is the starting zoom level.
        '''
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "maxscale_zoom" + str(zoomNum)
        return str(int(zoomScaleData.get(str(scaleDenKey))) + 1)

    def getMinDenominator(self, zoomNum):
        '''
        Returns the denominator for the minimum zoom at given zoom level.
        This is the ending zoom level.
        '''
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "maxscale_zoom" + str(zoomNum)
        return str(int(zoomScaleData.get(str(scaleDenKey))) - 1)

    def _add_Text_Style(self, field, labelType, minScale, maxScale, breakZoom):
        '''
        Adds styles for country labels. On lower zooms, when only country
        labels are shown, font size is larger. Break zoom specifies when
        the article labels start showing.
        '''
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1] + 'LabelStyle')
        rule = SubElement(style, 'Rule')

        minScaleSym = SubElement(rule, 'MinScaleDenominator')
        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        minScaleSym.text = self.getMinDenominator(maxScale + breakZoom)
        maxScaleSym.text = self.getMaxDenominator(maxScale)

        textSym = SubElement(rule, 'TextSymbolizer', placement=labelType)
        textSym.text = field
        textSym.set('face-name', 'Geo Bold')
        textSym.set('size', '20')
        textSym.set('wrap-width', '100')
        textSym.set('placement-type', 'simple')
        textSym.set('placements', 'N,S,19,18,17,16')
        textSym.set('opacity', '0.65')

        rule = SubElement(style, 'Rule')

        minScaleSym = SubElement(rule, 'MinScaleDenominator')
        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        minScaleSym.text = self.getMinDenominator(minScale)
        maxScaleSym.text = self.getMaxDenominator(maxScale + breakZoom)

        textSym = SubElement(rule, 'TextSymbolizer', placement=labelType)
        textSym.text = field
        textSym.set('face-name', 'Geo Bold')
        textSym.set('size', '30')
        textSym.set('wrap-width', '100')
        textSym.set('placement-type', 'simple')
        textSym.set('placements', 'N,S,29,28,27,26')
        textSym.set('opacity', '0.5')

    def _add_Filter_Rules(self, field, labelType, filterZoomNum, imgFile, numBins):
        '''
        Adds filter rules for styles. Maxzoom specifies when article labels
        show up on map. Size of labels are determined by their popularity
        bin score.

        Invisible points are added to allow for interactivity from UTF grids.

        Less opaque points show up one zoom level before their labels show up.
        '''
        style = SubElement(self.mapRoot, 'Style', 
                           name=field[1:-1] + str(filterZoomNum) + 'LabelStyle')
        sizeLabel = 10

        for b in range(numBins):
            rule = SubElement(style, 'Rule')
            filterBy = SubElement(rule, 'Filter')
            filterBy.text = "[maxzoom] <= " + str(filterZoomNum) + " and [popbinscore] = " + str(b) + ""

            maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
            maxScaleSym.text = self.getMaxDenominator(filterZoomNum)

            shieldSym = SubElement(rule, 'ShieldSymbolizer',
                                   placement=labelType)
            shieldSym.text = field
            shieldSym.set('dy', '-10')
            shieldSym.set('unlock-image', 'true')

            shieldSym.set('file', imgFile)
            shieldSym.set('avoid-edges', 'true')
            # shieldSym.set('minimum-padding', '120')
            shieldSym.set('wrap-width', '50')

            shieldSym.set('face-name', 'GeosansLight Regular')
            shieldSym.set('size', str(sizeLabel))

            shieldSym.set('placement-type', 'simple')
            placementList = 'N,S,' + str((sizeLabel - 1)) + ',' +  \
                            str((sizeLabel - 2)) + ',' + str((sizeLabel - 3))
            shieldSym.set('placements', placementList)

            sizeLabel += 3

       # Invisible points added 
        rule = SubElement(style, 'Rule')
        filterBy = SubElement(rule, 'Filter')
        filterBy.text = "[maxzoom] <= " + str(filterZoomNum)

        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        maxScaleSym.text = self.getMaxDenominator(filterZoomNum)
        assert maxScaleSym.text is not None, 'no max denominator for %s' % filterZoomNum

        pointSym = SubElement(rule, 'PointSymbolizer')
        pointSym.set('file', imgFile)
        pointSym.set('opacity', '0.0')

        pointSym.set('ignore-placement', 'true')
        pointSym.set('allow-overlap', 'true')

        # Opaque points that show up before labels.
        rule = SubElement(style, 'Rule')
        filterBy = SubElement(rule, 'Filter')
        filterBy.text = "[maxzoom] = " + str(filterZoomNum + 1)

        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        maxScaleSym.text = self.getMaxDenominator(filterZoomNum)
        assert maxScaleSym.text != None, 'no max denominator for %s' % filterZoomNum

        pointSym = SubElement(rule, 'PointSymbolizer')
        pointSym.set('file', imgFile)
        pointSym.set('opacity', '0.3')

        pointSym.set('ignore-placement', 'true')
        pointSym.set('allow-overlap', 'false')




    def _add_Shield_Style_By_Zoom(self, field, labelType, maxZoom, imgFile, numBins):
        '''
        Associate the every zoom's rules with their style.
        '''
        for z in range(maxZoom):
            self._add_Filter_Rules(field, labelType, z, imgFile, numBins)

    def _add_Text_Layer(self, field):
        '''
        Links country label styles and datasource to a layer.
        '''
        layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + 'Layer')
        layer.set('srs', '+init=epsg:4236')
        layer.set('cache-features', 'true')

        addStyle = SubElement(layer, 'StyleName')
        addStyle.text = field[1:-1] + 'LabelStyle'

        self.addDataSource(layer, self.table)

    def _add_Shield_Layer_By_Zoom(self, field, maxZoom):
        '''
        Specifies shields (points and labels) of articles and the
        datasource with its respective layer.
        '''
        for z in reversed(range(maxZoom)):
            layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + str(z) + 'Layer')
            layer.set('srs', '+init=epsg:4236')
            layer.set('cache-features', 'true')
            layer.set('minzoom', self.getMinDenominator(z))
            layer.set('maxzoom', self.getMaxDenominator(z))
            assert layer.get('minzoom') is not None, 'no min denominator for %s' % z
            assert layer.get('maxzoom') is not None, 'no max denominator for %s' % z
            addStyle = SubElement(layer, 'StyleName')
            addStyle.text = field[1:-1] + str(z) + 'LabelStyle'
            if z != maxZoom:
                self.addDataSource(layer, '(select * from ' + self.table + ' where maxzoom <= ' + str(z+1) + ' order by maxzoom) as foo')
            else:
                self.addDataSource(layer, '(select * from ' + self.table + ' where maxzoom <= ' + str(z) + ' order by maxzoom) as foo')

    def writeLabelsByZoomToXml(self, field, labelType, maxZoom, imgFile, numBins):
        '''
        Writes out the style and layer for article labels to xml.
        '''
        self._add_Shield_Style_By_Zoom(field, labelType, maxZoom, imgFile, numBins)
        self._add_Shield_Layer_By_Zoom(field, maxZoom)
        self.write()

    def writeLabelsXml(self, field, labelType, breakZoom, minScale='1066', maxScale='559082264'):
        '''
        Writes out the style and layer for country labels to the xml.
        '''
        self._add_Text_Style(field, labelType, minScale, maxScale, breakZoom)
        self._add_Text_Layer(field)
        self.write()

    def addDataSource(self, parent, table):
        '''
        Add a specific postSQL database table to a given layer.
        '''
        data = SubElement(parent, 'Datasource')

        def addParam(name, text):
            SubElement(data, 'Parameter', name=name).text = text
        addParam('type', 'postgis')
        addParam('table', table)
        addParam('max_async_connection', '4')
        addParam('geometry_field', 'geom')
        addParam('host', self.config.get('PG', 'host'))
        addParam('dbname', self.config.get('PG', 'database'))

        if self.config.get('PG', 'user'):
            addParam('user', self.config.get('PG', 'user'))
        if self.config.get('PG', 'password'):
            addParam('password', self.config.get('PG', 'password'))

    def write(self):
        '''
        Writes out additions to the generated map xml file.
        '''
        self.mapFile.write(self.mapFileName, encoding='utf-8')
        parser = letree.XMLParser(remove_blank_text=True)
        tree = letree.parse(self.mapFileName, parser)
        tree.write(self.mapFileName, pretty_print=True)

    # For testing purposes. Move this elsewhere.
    def embossContinents(self, threeD=False):
        '''
        Adding embossing and translate to countries so they "pop-out"
        from the ocean.

        The threeD feature embosses the contours thereby giving the map a
        3-dimensional look. Note that this feature takes a long time for
        the map to load.
        '''
        for elem in self.mapFile.iterfind('Style[@name="countries"]'):
            elem.set('image-filters', 'emboss, blur')
            elem.set('transform', 'translate(10,10)')

        if threeD:
            for i in range(100):
                for elem in self.mapFile.iterfind('Style[@name="contour%s"]' % (i)):
                    elem.set('image-filters', 'emboss, blur')
