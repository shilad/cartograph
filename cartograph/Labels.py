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

    def getScaleDenominator(self, zoomNum):
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "maxscale_zoom" + str(zoomNum)
        return zoomScaleData.get(str(scaleDenKey))

    def _add_Text_Style(self, field, labelType, minScale, maxScale):
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1] + 'LabelStyle')
        rule = SubElement(style, 'Rule')

        minScaleSym = SubElement(rule, 'MinScaleDenominator')
        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        minScaleSym.text = str(minScale)
        maxScaleSym.text = str(maxScale)

        textSym = SubElement(rule, 'TextSymbolizer', placement=labelType)
        textSym.text = field
        textSym.set('face-name', 'DejaVu Sans Book')
        textSym.set('size', '12')


    def _add_Filter_Rules(self, field, labelType, filterZoomNum, imgFile):
        style = SubElement(self.mapRoot, 'Style', 
                           name=field[1:-1] + str(filterZoomNum) + 'LabelStyle')
        rule = SubElement(style, 'Rule')

        filterBy = SubElement(rule, 'Filter')
        filterBy.text = "[maxzoom] = " + str(filterZoomNum) +""

        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        maxScaleSym.text = self.getScaleDenominator(filterZoomNum)

        shieldSym = SubElement(rule, 'ShieldSymbolizer', placement=labelType)
        shieldSym.text = field
        shieldSym.set('face-name', 'DejaVu Sans Book')
        shieldSym.set('size', '12')
        shieldSym.set('dx', '15')
        shieldSym.set('unlock-image', 'true')
        shieldSym.set('placement-type', 'simple')
        shieldSym.set('file', imgFile)

    def _add_Shield_Style_By_Zoom(self, field, labelType, maxZoom, imgFile):
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1] + 'LabelStyle')
        for z in range(maxZoom):
            self._add_Filter_Rules(field, labelType, z, imgFile)

    def _add_Text_Layer(self, field):
        layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + 'Layer')
        layer.set('srs', '+init=epsg:4236')
        layer.set('cache-features', 'true')

        addStyle = SubElement(layer, 'StyleName')
        addStyle.text = field[1:-1] + 'LabelStyle'

        self.addDataSource(layer, self.table)

    def _add_Shield_Layer_By_Zoom(self, field, maxZoom):
        for z in range(maxZoom):
            layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + str(z) + 'Layer')
            layer.set('srs', '+init=epsg:4236')
            layer.set('cache-features', 'true')
            layer.set('minzoom', '0')
            layer.set('maxzoom', self.getScaleDenominator(z))
            addStyle = SubElement(layer, 'StyleName')
            addStyle.text = field[1:-1] + str(z) + 'LabelStyle'
            self.addDataSource(layer, '(select * from ' + self.table + ' where maxzoom = ' + str(z) + ') as foo')

    def writeLabelsByZoomToXml(self, field, labelType, maxZoom, imgFile):
        self._add_Shield_Style_By_Zoom(field, labelType, maxZoom, imgFile)
        self._add_Shield_Layer_By_Zoom(field, maxZoom)
        self.write()

    def writeLabelsXml(self, field, labelType, minScale='1066', maxScale='559082264'):
        self._add_Text_Style(field, labelType, minScale, maxScale)
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

