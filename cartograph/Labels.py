from xml.etree.ElementTree import parse, SubElement

import Util

import lxml.etree as letree



class Labels():
    def __init__(self, config, mapfile, table, scaleDimensions):
        self.config = config
        self.mapFileName = mapfile
        self.mapFile = parse(mapfile)
        self.table = table
        self.mapRoot = self.mapFile.getroot()
        self.zoomScaleData = Util.read_zoom(scaleDimensions)

    def addCustomFonts(self,fontDir):
        self.mapRoot.set('font-directory',fontDir)

    def getMaxDenominator(self, zoomNum):
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "maxscale_zoom" + str(zoomNum)
        return str(int(zoomScaleData.get(str(scaleDenKey))) + 1)

    def getMinDenominator(self, zoomNum):
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "maxscale_zoom" + str(zoomNum)
        return str(int(zoomScaleData.get(str(scaleDenKey))) - 1)

    def _add_Text_Style(self, field, labelType, minScale, maxScale, breakZoom):
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1] + 'LabelStyle')
        rule = SubElement(style, 'Rule')

        minScaleSym = SubElement(rule, 'MinScaleDenominator')
        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        minScaleSym.text = self.getMinDenominator(maxScale + breakZoom)
        maxScaleSym.text = self.getMaxDenominator(maxScale)

        textSym = SubElement(rule, 'TextSymbolizer', placement=labelType)
        textSym.text = field
        textSym.set('face-name', 'Geo Bold')
        textSym.set('size', '18')
        textSym.set('wrap-width', '100')
        textSym.set('placement-type', 'simple')
        textSym.set('placements', 'N,S,14,13,12,11')
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
        style = SubElement(self.mapRoot, 'Style', 
                           name=field[1:-1] + str(filterZoomNum) + 'LabelStyle')
        sizeLabel = 8

        for b in range(numBins):
            rule = SubElement(style, 'Rule')
            filterBy = SubElement(rule, 'Filter')
            filterBy.text = "[maxzoom] <= " + str(filterZoomNum) + " and [popbinscore] = " + str(b) + ""

            #minScaleSym = SubElement(rule, 'MinScaleDenominator').text = '2133'
            maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
            maxScaleSym.text = self.getMaxDenominator(filterZoomNum)

            shieldSym = SubElement(rule, 'ShieldSymbolizer', placement = labelType)
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
            placementList = 'N,S,' + str((sizeLabel-1)) + ',' + str((sizeLabel-2)) + ',' + str((sizeLabel-3))
            shieldSym.set('placements', placementList)

            sizeLabel += 3

        for c in range(1):
            rule = SubElement(style, 'Rule')
            filterBy = SubElement(rule, 'Filter')
            filterBy.text = "[maxzoom] <= " + str(filterZoomNum)

            #minScaleSym = SubElement(rule, 'MinScaleDenominator').text = '2133'
            maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
            maxScaleSym.text = self.getMaxDenominator(filterZoomNum)
            assert maxScaleSym.text != None, 'no max denominator for %s' % filterZoomNum

            pointSym = SubElement(rule, 'PointSymbolizer')
            pointSym.set('file', imgFile)
            pointSym.set('opacity', '0.0')

            pointSym.set('ignore-placement', 'true')
            pointSym.set('allow-overlap', 'true')


    def _add_Shield_Style_By_Zoom(self, field, labelType, maxZoom, imgFile, numBins):
        for z in range(maxZoom):
            self._add_Filter_Rules(field, labelType, z, imgFile, numBins)

    def _add_Text_Layer(self, field):
        layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + 'Layer')
        layer.set('srs', '+init=epsg:4236')
        layer.set('cache-features', 'true')

        addStyle = SubElement(layer, 'StyleName')
        addStyle.text = field[1:-1] + 'LabelStyle'

        self.addDataSource(layer, self.table)

    def _add_Shield_Layer_By_Zoom(self, field, maxZoom):
        for z in reversed(range(maxZoom)):
            layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + str(z) + 'Layer')
            layer.set('srs', '+init=epsg:4236')
            layer.set('cache-features', 'true')
            layer.set('minzoom', self.getMinDenominator(z))
            layer.set('maxzoom', self.getMaxDenominator(z))
            assert layer.get('minzoom') != None, 'no min denominator for %s' % z
            assert layer.get('maxzoom') != None, 'no max denominator for %s' % z
            addStyle = SubElement(layer, 'StyleName')
            addStyle.text = field[1:-1] + str(z) + 'LabelStyle'
            self.addDataSource(layer, '(select * from ' + self.table + ' where maxzoom <= ' + str(z) + ' order by maxzoom) as foo')

    def writeLabelsByZoomToXml(self, field, labelType, maxZoom, imgFile, numBins):
        self._add_Shield_Style_By_Zoom(field, labelType, maxZoom, imgFile, numBins)
        self._add_Shield_Layer_By_Zoom(field, maxZoom)
        self.write()

    def writeLabelsXml(self, field, labelType, breakZoom, minScale='1066', maxScale='559082264'):
        self._add_Text_Style(field, labelType, minScale, maxScale, breakZoom)
        self._add_Text_Layer(field)
        self.write()

    def addDataSource(self, parent, table):
        data = SubElement(parent, 'Datasource')
        def addParam(name, text): 
            SubElement(data, 'Parameter', name=name).text = text
        addParam('type', 'postgis')
        addParam('table', table)
        addParam('max_async_connection', '4')
        addParam('geometry_field', 'geom')
        addParam('host', self.config.get('PG', 'host'))
        addParam('dbname', self.config.get('PG', 'database'))
        #addParam('estimate_extent', 'true')
        if self.config.get('PG', 'user'):
            addParam('user', self.config.get('PG', 'user'))
        if self.config.get('PG', 'password'):
            addParam('password', self.config.get('PG', 'password'))

    def write(self):
        self.mapFile.write(self.mapFileName, encoding='utf-8')
        parser = letree.XMLParser(remove_blank_text=True)
        tree = letree.parse(self.mapFileName, parser)
        tree.write(self.mapFileName, pretty_print=True)

    #For stesting purposes. Move this elsewhere. 
    def addWaterXml(self):
        for elem in self.mapFile.iterfind('Style[@name="countries"]'):
            elem.set('image-filters', 'emboss')
 

