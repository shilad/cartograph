import os
import logging
import types


logger = logging.getLogger('cartograph.config')

from ConfigParser import SafeConfigParser

EXTERNAL_FILES = 'ExternalFiles'
PREPROCESSING_FILES = 'GeneratedFiles'
PREPROCESSING_CONSTANTS = 'PreprocessingConstants'
MAP_CONSTANTS = 'MapConstants'
MAP_DATA = 'MapData'
MAP_IMG_RESOURCES = 'MapResources'
MAP_OUTPUT = 'MapOutput'

_requiredSections = [EXTERNAL_FILES, PREPROCESSING_FILES,
                     PREPROCESSING_CONSTANTS, MAP_CONSTANTS,
                     MAP_DATA, MAP_IMG_RESOURCES, MAP_OUTPUT]

CONFIG = None
COLORWHEEL = None

def get():
    global CONFIG

    if not CONFIG:
        initConf()
    return CONFIG

def getColorWheel():
    global COLORWHEEL

    if not COLORWHEEL:
        conf = get()
        num_clusters = conf.getint(PREPROCESSING_CONSTANTS, 'num_clusters')
        COLORWHEEL = _coloringFeatures(num_clusters)

    return COLORWHEEL

def samplePath(origPath, n):
    i = origPath.rfind('.')
    if i < 0:
        return '%s.sample_%s' % (origPath, n)
    else:
        return '%s.sample_%s.%s' % (origPath[:i], n, origPath[i + 1:])


def initConf(confFile=None):
    global CONFIG

    conf = SafeConfigParser()
    with open("./data/conf/defaultconfig.txt", "r") as configFile:
        conf.readfp(configFile)

    if confFile is None:
        confFile = os.environ.get('CARTOGRAPH_CONF', 'conf.txt')
    logger.info('using configuration file %s' % (`confFile`))

    if os.path.isfile(confFile):
        with open(confFile, "r") as updateFile:
            conf.readfp(updateFile)
    else:
        logger.warn('configuration file %s does not exist' % (`confFile`))

    def confSample(target, section, key, n=None):
        if n is None:
            n = target.getint('PreprocessingConstants', 'sample_size')
        return samplePath(target.get(section, key), n)

    conf.getSample = types.MethodType(confSample, conf)

    CONFIG = conf


def _verifyRequiredSections(conf, requiredSections):
    confSections = conf.sections()
    for section in requiredSections:
        if section not in confSections:
            raise Exception, 'Missing config section %s' % (section,)


def selective_merge(base_obj, delta_obj):
    """
    Merges a delta configuration object into a base configuration.
    See http://stackoverflow.com/a/29124916/141245
    """
    if not isinstance(base_obj, dict):
        return delta_obj
    common_keys = set(base_obj).intersection(delta_obj)
    new_keys = set(delta_obj).difference(common_keys)
    for k in common_keys:
        base_obj[k] = selective_merge(base_obj[k], delta_obj[k])
    for k in new_keys:
        base_obj[k] = delta_obj[k]
    return base_obj


def _coloringFeatures(num_clusters):
    '''
    Chooses number of colors to be included in the color wheel
    based on the number of clusters.
    '''
    assert(num_clusters <= 30)
    colors = {0: {6: "#b79c29", 5: "#bea53e", 4: "#c5af53", 3: "#ccb969", 2: "#d3c37e", 1: "#dbcd94", 0: "#e2d7a9", 7: "#e9e1be"},
                1: {6: "#905a6e", 5: "#9b6a7c", 4: "#a67a8b", 3: "#b18b99", 2: "#bc9ca8", 1: "#c7acb6", 0: "#d2bdc5", 7: "#ddcdd3"},
                2: {6: "#7eab2b", 5: "#8ab340", 4: "#97bb55", 3: "#a4c46a", 2: "#b1cc7f", 1: "#bed595", 0: "#cbddaa", 7: "#d8e5bf"},
                3: {6: "#f10e0a", 5: "#f6221e", 4: "#f73a36", 3: "#f8524f", 2: "#f96a68", 1: "#fa8280", 0: "#fb9a99", 7: "#fcb2b2"},
                4: {6: "#4f3b73", 5: "#5a4484", 4: "#664c95", 3: "#7155a6", 2: "#7f65b0", 1: "#8d75b9", 0: "#9b86c1", 7: "#a997ca"},
                5: {6: "#bd890b", 5: "#d59a0d", 4: "#edac0e", 3: "#f2b523", 2: "#f3bd3b", 1: "#f5c553", 0: "#f6cd6b", 7: "#f7d583"},
                6: {6: "#175197", 5: "#1a5dad", 4: "#1e69c3", 3: "#2175d9", 2: "#3382e0", 1: "#4a90e3", 0: "#609de7", 7: "#76abea"},
                7: {6: "#cd5000", 5: "#d26119", 4: "#d77232", 3: "#dc844c", 2: "#e19666", 1: "#e6a77f", 0: "#ebb999", 7: "#f0cab2"},
                8: {6: "#0eb19a", 5: "#26b8a4", 4: "#3ec0ae", 3: "#56c8b8", 2: "#6ed0c2", 1: "#86d8cc", 0: "#9edfd6", 7: "#b6e7e0"},
                9: {6: "#df0055", 5: "#e21966", 4: "#e53276", 3: "#e84c88", 2: "#eb6699", 1: "#ef7faa", 0: "#f299bb", 7: "#f5b2cc"},
                10: {6: "#205f16", 5: "#366f2d", 4: "#4c7e44", 3: "#628f5b", 2: "#799f73", 1: "#8faf8a", 0: "#a5bfa1", 7: "#bccfb9"},
                11: {6: "#db83a4", 5: "#de8fad", 4: "#e29bb6", 3: "#e5a8bf", 2: "#e9b4c8", 1: "#edc1d1", 0: "#f0cdda", 7: "#f4d9e3"},
                12: {6: "#00a91f", 5: "#19b135", 4: "#32ba4b", 3: "#4cc262", 2: "#66cb78", 1: "#7fd48f", 0: "#99dca5", 7: "#b2e5bb"},
                13: {6: "#6e4278", 5: "#7c5485", 4: "#8b6793", 3: "#997aa0", 2: "#a88dae", 1: "#b6a0bb", 0: "#c5b3c9", 7: "#d3c6d6"},
                14: {6: "#5eaf65", 5: "#6eb774", 4: "#7ebf83", 3: "#8ec793", 2: "#9ecfa2", 1: "#aed7b2", 0: "#bedfc1", 7: "#cee7d0"},
                15: {6: "#d600a9", 5: "#da19b1", 4: "#de32ba", 3: "#e24cc2", 2: "#e666cb", 1: "#ea7fd4", 0: "#ee99dc", 7: "#f2b2e5"},
                16: {6: "#a2a161", 5: "#abaa70", 4: "#b4b380", 3: "#bdbd90", 2: "#c7c6a0", 1: "#d0d0b0", 0: "#d9d9bf", 7: "#e3e2cf"},
                17: {6: "#1a45ed", 5: "#3057ee", 4: "#476af0", 3: "#5e7cf2", 2: "#758ff4", 1: "#8ca2f6", 0: "#a3b4f7", 7: "#bac7f9"},
                18: {6: "#724b01", 5: "#805d1a", 4: "#8e6e33", 3: "#9c814d", 2: "#aa9366", 1: "#b8a580", 0: "#c6b799", 7: "#d4c9b2"},
                19: {6: "#ff4afa", 5: "#ff5cfa", 4: "#ff6efb", 3: "#ff80fb", 2: "#ff92fc", 1: "#ffa4fc", 0: "#ffb6fd", 7: "#ffc8fd"},
                20: {6: "#947a00", 5: "#9e8719", 4: "#a99432", 3: "#b4a14c", 2: "#beaf66", 1: "#c9bc7f", 0: "#d4c999", 7: "#ded7b2"},
                21: {6: "#7132a5", 5: "#7f46ae", 4: "#8d5ab7", 3: "#9b6fc0", 2: "#a984c9", 1: "#b898d2", 0: "#c6addb", 7: "#d4c1e4"},
                22: {6: "#557700", 5: "#668419", 4: "#769232", 3: "#889f4c", 2: "#99ad66", 1: "#aabb7f", 0: "#bbc899", 7: "#ccd6b2"},
                23: {6: "#dc7bd0", 5: "#df88d4", 4: "#e395d9", 3: "#e6a2de", 2: "#eaafe2", 1: "#edbde7", 0: "#f1caec", 7: "#f4d7f0"},
                24: {6: "#e4003d", 5: "#e61950", 4: "#e93263", 3: "#ec4c77", 2: "#ee668a", 1: "#f17f9e", 0: "#f499b1", 7: "#f6b2c4"},
                25: {6: "#006aa1", 5: "#1978aa", 4: "#3287b3", 3: "#4c96bd", 2: "#66a5c6", 1: "#7fb4d0", 0: "#99c3d9", 7: "#b2d2e2"},
                26: {6: "#f27a72", 5: "#f38780", 4: "#f4948e", 3: "#f5a19c", 2: "#f7afaa", 1: "#f8bcb8", 0: "#f9c9c6", 7: "#fbd7d4"},
                27: {6: "#0061b0", 5: "#1970b7", 4: "#3280bf", 3: "#4c90c7", 2: "#66a0cf", 1: "#7fb0d7", 0: "#99bfdf", 7: "#b2cfe7"},
                28: {6: "#a11837", 5: "#aa2f4b", 4: "#b3465e", 3: "#bd5d73", 2: "#c67487", 1: "#d08b9b", 0: "#d9a2af", 7: "#e2b9c3"},
                29: {6: "#cf7ced", 5: "#d389ee", 4: "#d896f0", 3: "#dda3f2", 2: "#e2b0f4", 1: "#e7bdf6", 0: "#ebcaf7", 7: "#f0d7f9"}}

    keys = colors.keys()[:num_clusters]
    for key in colors.keys():
        if key not in keys:
            del colors[key]
    return colors