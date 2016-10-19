from cartograph import Utils


class ZoomTSVWriter:
    def __init__(self, config):
        self.config = config

    def writeZoomTSV(self):
        zoomDict = Utils.read_features(self.config.get("GeneratedFiles", "zoom_with_id"),
                                       self.config.get("ExternalFiles", "names_with_id"))
        #THIS NEEDS TO CHANGE TO BE PART OF THE CONFIG FILE, BUT I'M HARDCODING IT FOR NOW
        filepath = "./web/data/named_zoom.tsv"
        with open(filepath, "a") as writeFile:
            #hardcoded and inelegant, but it works and it's just a data file that only needs to be generated once so...
            writeFile.write('name\tmaxZoom\n')
            for entry in zoomDict:
                name = zoomDict[entry]['name']
                zoom = zoomDict[entry]['maxZoom']
                writeFile.write(name + "\t" + zoom + "\n")
