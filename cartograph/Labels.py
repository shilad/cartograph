from xml.etree.ElementTree import parse, SubElement


class Labels():
    def __init__(self, filename):
        self.filename = filename
        self.mapFile = parse(filename)
        self.mapRoot = self.mapFile.getroot()

#     def _add_Zoom_Ref(self):
# <?xml version="1.0" encoding="utf-8"?>
# <!DOCTYPE Map [
# <!ENTITY % entities SYSTEM "data/zoomScales.xml.inc">
# %entities;
# ]>


    def _add_Text_Style(self, field, labelType, minScale, maxScale):
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1] + 'LabelStyle')
        rule = SubElement(style, 'Rule')

        minScaleSym = SubElement(rule,'MinScaleDenominator')
        maxScaleSym = SubElement(rule,'MaxScaleDenominator')
        minScaleSym.text = minScale
        maxScaleSym.text = maxScale

        textSym = SubElement(rule, 'TextSymbolizer', placement=labelType)
        textSym.text = field
        textSym.set('face-name', 'DejaVu Sans Book')
        textSym.set('size', '12')

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

    def writeLabelsXml(self, field, labelType, geojsonFile, mapFile, minScale=1066, maxScale=559082264):
        self._add_Text_Style(field, labelType, minScale, maxScale)
        self._add_Text_Layer(field, geojsonFile)
        self.mapFile.write(mapFile)
