from xml.etree.ElementTree import parse, SubElement
import Util
import Config

config = Config.BAD_GET_CONFIG()

class Labels():
    def __init__(self, mapfile, geojson):
        self.mapFileName = mapfile
        self.mapFile = parse(mapfile)
        self.geojson = geojson
        self.mapRoot = self.mapFile.getroot()
        self.zoomScaleData = Util.read_zoom(config.FILE_NAME_SCALE_DENOMINATORS)

    def getMaxDenominator(self, zoomNum):
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "maxscale_zoom" + str(zoomNum)
        return zoomScaleData.get(str(scaleDenKey))

    def getMinDenominator(self, zoomNum):
        zoomScaleData = self.zoomScaleData
        scaleDenKey = "minscale_zoom" + str(zoomNum)
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

    def _add_Zoom_Filter_Rules(self, style, zoomField, labelType, filterZoomNum, imgFile, numBins):
        rule = SubElement(style, 'Rule')
        sizeLabel = 12

        for b in range(numBins):
            filterBy = SubElement(rule, 'Filter')
            filterBy.text = str(zoomField) + ".match('" + str(filterZoomNum) +"') and " + "[popBinScore].match('" + str(b) + "')"

            maxScaleSym = SubElement(rule, 'MaxScaleDenominator')
            maxScaleSym.text = self.getMaxDenominator(filterZoomNum)

            shieldSym = SubElement(rule, 'ShieldSymbolizer', placement=labelType)
            shieldSym.text = zoomField
            shieldSym.set('dx', '15')
            shieldSym.set('unlock-image', 'true')
            shieldSym.set('placement-type', 'simple')
            shieldSym.set('file', imgFile)

            shieldSym.set('face-name', 'DejaVu Sans Book')
            shieldSym.set('size', str(sizeLabel))
            sizeLabel += 5

    def _add_Shield_Style_By_Zoom(self, field, labelType, maxZoom, imgFile, numBins):
        style = SubElement(self.mapRoot, 'Style', name=field[1:-1]+'LabelStyle')
        for z in range(maxZoom):
            self._add_Zoom_Filter_Rules(style, field, labelType, z, imgFile, numBins)

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

    def _add_Shield_Layer_By_Zoom(self, field, geojsonFile):
        layer = SubElement(self.mapRoot, 'Layer', name=field[1:-1] + 'Layer')
        layer.set('srs', '+init=epsg:4236')

        addStyle = SubElement(layer, 'StyleName')
        addStyle.text = field[1:-1] + 'LabelStyle'

        data = SubElement(layer, 'Datasource')
        dataParamType = SubElement(data, 'Parameter', name='type')
        dataParamType.text = 'geojson'
        dataParamFile = SubElement(data, 'Parameter', name='file')
        dataParamFile.text = geojsonFile

    def writeLabelsByZoomToXml(self, field, labelType, maxZoom, imgFile, numBins):
        self._add_Shield_Style_By_Zoom(field, labelType, maxZoom, imgFile, numBins)
        self._add_Shield_Layer_By_Zoom(field, self.geojson)
        self.mapFile.write(self.mapFileName)

    def writeLabelsXml(self, field, labelType, minScale='1066', maxScale='559082264'):
        self._add_Text_Style(field, labelType, minScale, maxScale)
        self._add_Text_Layer(field, self.geojson)
        self.mapFile.write(self.mapFileName)
