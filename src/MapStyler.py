import mapnik

class MapStyler:
    def __init__(self):
        self.m = None

    def makeMap(self, contourFilename, countryFilename, width=1200, height=600):
        self.m = mapnik.Map(width, height)
        self.m.background = mapnik.Color('white')
 
        self.m.append_style("contour", generateSinglePolygonStyle(contourFilename, 0, 1))
        self.m.layers.append(generateLayer(contourFilename,
                                      "contour", "contour"))
 
        self.m.append_style("outline", generateLineStyle("darkblue", 0))
        self.m.layers.append(generateLayer(contourFilename,
                                      "outline", "outline"))
 
        self.m.append_style("countries", generateCountryPolygonStyle(countryFilename, 1.0))
        self.m.layers.append(generateLayer(countryFilename, "countries", "countries"))
        self.m.zoom_all()

    def saveMapXml(self, countryFilename, mapFilename):
        assert(self.m != None)
        self.m.save_map(m, mapFilename)
        label = Labels.Labels(mapFilename)
        label.writeLabelsXml('[labels]', 'interior', countryFilename)

    def saveImage(self, imgFilename):
        mapnik.render_to_file(self.m, imgFilename)
