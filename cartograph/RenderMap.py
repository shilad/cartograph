import luigi
import Config
import Utils
import Colors
from Labels import LabelMapUsingZoom
from MapStyler import CreateMapXml, MapStylerCode, MapStyler
from LuigiUtils import MTimeMixin, TimestampedLocalTarget


class RenderMap(MTimeMixin, luigi.Task):
    '''
    Write the final product xml of all our data manipulations to an image file
    to ensure that everything excuted as it should
    '''
    def requires(self):
        return (CreateMapXml(),
                LabelMapUsingZoom(),
                MapStylerCode(),
                Colors.ColorsCode())

    def output(self):
        config = Config.get()
        return(
            TimestampedLocalTarget(config.get("MapOutput",
                                              "img_src_name") + '.png'),
            TimestampedLocalTarget(config.get("MapOutput",
                                              "img_src_name") + '.svg'))

    def run(self):
        config = Config.get()
        colorWheel = Config.getColorWheel()
        countryBorders = Utils.read_features(config.get("GeneratedFiles", "country_borders"))
        colorFactory = Colors.ColorSelector(countryBorders, colorWheel)
        colors = colorFactory.optimalColoring()
        ms = MapStyler(config, colors)
        ms = MapStyler(config, colorWheel)
        ms.saveImage(config.get("MapOutput", "map_file_density"),
                     config.get("MapOutput", "img_src_name") + ".png")
        ms.saveImage(config.get("MapOutput", "map_file_density"),
                     config.get("MapOutput", "img_src_name") + ".svg")
