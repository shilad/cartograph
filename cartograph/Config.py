
from ConfigParser import SafeConfigParser

EXTERNAL_FILES = 'ExternalFiles'
PREPROCESSING_FILES = 'PreprocessingFiles'
PREPROCESSING_CONSTANTS = 'PreprocessingConstants'
MAP_CONSTANTS = 'MapConstants'
MAP_DATA = 'MapData'
MAP_IMG_RESOURCES = 'MapResources'
MAP_OUTPUT = 'MapOutput'

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
    colorWheel = _coloringFeatures(num_clusters)
    colorWheel = [["#6caed1", "#7fb9d7", "#93c3dd", "#a6cee3", "#b9d9e9", "#cde3ef", "#e0eef5", "#f3f9fb"],
                ["#144c73", "#185b88", "#1b699e", "#1f78b4", "#2387ca", "#2b94db", "#419fde", "#57aae2"],
                ["#8acf4e", "#98d462", "#a5da76", "#b2df8a", "#bfe49e", "#cceab2", "#daefc6", "#e7f5da"],
                ["#20641c", "#267821", "#2d8c27", "#33a02c", "#39b432", "#40c837", "#53ce4b", "#66d35f"],
                ["#f8514f", "#f96968", "#fa8280", "#fb9a99", "#fcb2b2", "#fdcbca", "#fee3e3", "#fffcfc"],
                ["#9e1214", "#b51516", "#cc1719", "#e31a1c", "#e72f31", "#ea4648", "#ec5d5e", "#ef7475"],
                ["#fc9d24", "#fca93d", "#fdb456", "#fdbf6f", "#fdca88", "#fed5a1", "#fee1ba", "#feecd3"],
                ["#b35900", "#cc6600", "#e67200", "#ff7f00", "#ff8c1a", "#ff9933", "#ffa54d", "#ffb267"],
                ["#a880bb", "#b391c4", "#bfa1cd", "#cab2d6", "#d5c3df", "#e1d3e8", "#ece4f1", "#f8f5fa"],
                ["#442763", "#512f75", "#5d3688", "#6a3d9a", "#7744ac", "#8350ba", "#9062c1", "#9d74c8"],
                ["#ffff34", "#ffff4d", "#ffff67", "#ffff80", "#ffff9a", "#ffffb3", "#ffffcd", "#ffffe7"],
                ["#733a1a", "#87441f", "#9c4f23", "#b15928", "#c6632d", "#d2703a", "#d77f4e", "#dc8e63"],
                ["#82125b", "#98156b", "#af187a", "#c51b8a", "#db1e9a", "#e330a5", "#e647af", "#e95db9"]]
    return conf, colorWheel


def _verifyRequiredSections(conf, requiredSections):
    confSections = conf.sections()
    for section in requiredSections:
        if section not in confSections:
            conf.add_section(section)
            print "Adding section %s" % (section)


def _coloringFeatures(num_clusters):
        assert(num_clusters <= 30)
        colors = {0: {6: "#b79c29", 5: "#bea53e", 4: "#c5af53", 3: "#ccb969", 2: "#d3c37e", 1: "#dbcd94", 0: "#e2d7a9", 7: "#e9e1be"},
                1: {6: "#905a6e", 5: "#9b6a7c", 4: "#a67a8b", 3: "#b18b99", 2: "#bc9ca8", 1: "#c7acb6", 0: "#d2bdc5", 7: "#ddcdd3"},
                2: {6: "#7eab2b", 5: "#8ab340", 4: "#97bb55", 3: "#a4c46a", 2: "#b1cc7f", 1: "#bed595", 0: "#cbddaa", 7: "#d8e5bf"},
                3: {6: "#e60077", 5: "#e81984", 4: "#eb3292", 3: "#ed4c9f", 2: "#f066ad", 1: "#f27fbb", 0: "#f599c8", 7: "#f7b2d6"},
                4: {6: "#007f57", 5: "#198b67", 4: "#329878", 3: "#4ca589", 2: "#66b29a", 1: "#7fbfab", 0: "#99cbbb", 7: "#b2d8cc"},
                5: {6: "#e8843e", 5: "#ea9051", 4: "#ec9c64", 3: "#eea877", 2: "#f1b58b", 1: "#f3c19e", 0: "#f5cdb1", 7: "#f8dac5"},
                6: {6: "#009193", 5: "#199c9d", 4: "#32a7a8", 3: "#4cb2b3", 2: "#66bdbe", 1: "#7fc8c9", 0: "#99d3d3", 7: "#b2dede"},
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
