
from ConfigParser import SafeConfigParser
from os import getcwd

EXTERNAL_FILES = 'ExternalFiles'
PREPROCESSING_FILES = 'PreprocessingFiles'
PREPROCESSING_CONSTANTS = 'PreprocessingConstants'
MAP_CONSTANTS = 'MapConstants'
MAP_DATA = 'MapData'
MAP_IMG_RESOURCES = 'MapResources'
MAP_OUTPUT = 'MapOutput'
COLORWHEEL = []

_requiredSections = [EXTERNAL_FILES, PREPROCESSING_FILES,
                     PREPROCESSING_CONSTANTS, MAP_CONSTANTS,
                     MAP_DATA, MAP_IMG_RESOURCES, MAP_OUTPUT]


def initConf(confFile=None):
    conf = SafeConfigParser()
    with open("./data/conf/defaultconfig.txt", "r") as configFile:
        conf.readfp(configFile)

    if confFile is not None:
        with open(confFile, "r") as updateFile:
            conf.readfp(updateFile)

        _verifyRequiredSections(conf, _requiredSections)

    num_clusters = conf.getint(PREPROCESSING_CONSTANTS, 'num_clusters')
    conf.set(MAP_DATA, 'colorwheel', str(_coloringFeatures(num_clusters)))

    return conf


def _verifyRequiredSections(conf, requiredSections):
    confSections = conf.sections()
    for section in requiredSections:
        if section not in confSections:
            conf.add_section(section)
            print "Adding section %s" % (section)


def _coloringFeatures(num_clusters):
        assert(num_clusters < 50)
        colors = ["#f19daa", "#26cf58", "#a51cd7", "#70c946", "#5346f1",
                  "#7da400", "#9561ff", "#00711b", "#fd5cff", "#757b00",
                  "#6e76ff", "#da6500", "#0048be", "#ff6031", "#026fdc",
                  "#c3000f", "#019577", "#ff33c7", "#6bc789", "#af009b",
                  "#686300", "#d081ff", "#a4bc86", "#002084", "#ff8b55",
                  "#012870", "#d8ad6a", "#880076", "#eca473", "#210e3b",
                  "#ff9285", "#005492", "#8b1300", "#8ba3ff", "#653000",
                  "#f68ff6", "#4e0800", "#d5a1ef", "#350423", "#ff5596",
                  "#0074a0", "#ce007a", "#93634d", "#88005b", "#cea8d3",
                  "#540021", "#e5a0c4", "#80003e", "#ff86ac", "#512745"]

        return colors[:num_clusters]
