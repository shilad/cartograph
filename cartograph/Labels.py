from xml.etree.ElementTree import parse, SubElement


class Labels():
    def __init__(self, mapfile, geojson):
        self.mapFileName = mapfile
        self.mapFile = parse(mapfile)
        self.geojson = geojson
        self.mapRoot = self.mapFile.getroot()

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

    def _add_Shield_Style(self, field, labelType, minScale, maxScale, imgFile):
        style = SubElement(self.mapRoot,'Style', name=field[1:-1] + 'LabelStyle')
        rule = SubElement(style, 'Rule')

        minScaleSym = SubElement(rule, 'MinScaleDenominator')
        maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
        minScaleSym.text = str(minScale)
        maxScaleSym.text = str(maxScale)

        shieldSym = SubElement(rule, 'ShieldSymbolizer', placement=labelType)
        shieldSym.text = field
        shieldSym.set('face-name', 'DejaVu Sans Book')
        shieldSym.set('size', '12')
        shieldSym.set('dx', '20')
        shieldSym.set('unlock-image', 'true')
        shieldSym.set('placement-type', 'simple')
        shieldSym.set('file', imgFile)

    def _add_Text_Layer(self, field, geojsonFile):
        layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + 'Layer')
        layer.set('srs', '+init=epsg:4236')

        addStyle = SubElement(layer, 'StyleName')
        addStyle.text = field[1:-1] + 'LabelStyle'

        data = SubElement(layer, 'Datasource')
        dataParamType = SubElement(data, 'Parameter', name='type')
        dataParamType.text = 'geojson'
        dataParamFile = SubElement(data, 'Parameter', name='file')
        dataParamFile.text = geojsonFile

    def writeLabelsXml(self, field, labelType, minScale='1066', maxScale='559082264'):
        self._add_Text_Style(field, labelType, minScale, maxScale)
        self._add_Text_Layer(field, self.geojson)
        self.mapFile.write(self.mapFileName)

    def writeShieldXml(self, field, labelType, imgFile, minScale='1066', maxScale='559082264'):
        self._add_Shield_Style(field, labelType, minScale, maxScale, imgFile)
        self._add_Text_Layer(field, self.geojson)
        self.mapFile.write(self.mapFileName)