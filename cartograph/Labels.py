from xml.etree.ElementTree import parse, SubElement


class Labels():
    def __init__(self, filename):
        self.filename = filename
        self.mapFile = parse(filename)
        self.mapRoot = self.mapFile.getroot()

    def _add_Text_Style(self, field, labelType):
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1] + 'LabelStyle')
        rule = SubElement(style, 'Rule')
        textSym = SubElement(rule, 'TextSymbolizer', placement=labelType)
        textSym.text = field
        textSym.set('face-name', 'DejaVu Sans Book')
        textSym.set('size', '12')

    def _add_Text_Layer(self, field, geojsonFile):
        layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + 'Layer')

        addStyle = SubElement(layer, 'StyleName')
        addStyle.text = field[1:-1] + 'LabelStyle'

        data = SubElement(layer, 'Datasource')
        dataParamType = SubElement(data, 'Parameter', name='type')
        dataParamType.text = 'geojson'
        dataParamFile = SubElement(data, 'Parameter', name='file')
        dataParamFile.text = geojsonFile

    def writeLabelsXml(self, field, labelType, geojsonFile, mapFile):
        self._add_Text_Style(field, labelType)
        self._add_Text_Layer(field, geojsonFile)
        self.mapFile.write(mapFile)
