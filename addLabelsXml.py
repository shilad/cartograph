from xml.etree import ElementTree as ET
from xml.etree.ElementTree import parse, Element, SubElement


def addTextStyle(mapRoot, field, labelType):
	style = SubElement(mapRoot,'Style', name = field[1:-1] + 'LabelStyle')
	rule = SubElement(style, 'Rule')
	textSym = SubElement(rule, 'TextSymbolizer', placement = labelType)
	textSym.text = field 
	textSym.set('face-name', 'DejaVu Sans Book')

def addTextLayer(mapRoot, field, geojsonFile):
	layer = SubElement(mapRoot, 'Layer', name =  field[1:-1] + 'Layer')

	addStyle = SubElement(layer, 'StyleName')
	addStyle.text = field[1:-1] + 'labelStyle'

	data = SubElement(layer, 'Datasource')
	dataParamType = SubElement(data, 'Parameter', name = 'type')
	dataParamType.text = 'geojson'
	dataParamFile = SubElement(data, 'Parameter', name = 'file')
	dataParamFile.text = geojsonFile

def writeLabelsXml(field, labelType, geojsonFile):
	mapFile = parse('map.xml')
	mapRoot = mapFile.getroot()

	addTextStyle(mapRoot,field,labelType)
	addTextLayer(mapRoot,field, geojsonFile)
	mapFile.write('map.xml')
	
