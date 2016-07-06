import ConfigParser

class Config:
    def __init__(self):
        self.FILE_NAME_WIKIBRAIN_VECS = "./data/labdata/vecs.tsv"
        self.FILE_NAME_WIKIBRAIN_NAMES = "./data/labdata/names.tsv"
        self.FILE_NAME_NUMBERED_VECS = "./data/labdata/numberedVecsFull.tsv"
        self.FILE_NAME_NUMBERED_NAMES = "./data/labdata/numberedNamesFull.tsv"
        self.FILE_NAME_ARTICLE_EMBEDDING = "./data/labdata/tsne_cache_full.tsv"
        self.FILE_NAME_ARTICLE_COORDINATES = "./data/tsv/coordinates.tsv"
        self.FILE_NAME_WATER_AND_ARTICLES = "./data/tsv/water_and_article_coordinates.tsv"
        self.FILE_NAME_WATER_CLUSTERS = "./data/tsv/clusters_with_water_pts.tsv"
        self.FILE_NAME_NUMBERED_CLUSTERS = "./data/tsv/numberedClusters.tsv"
        self.FILE_NAME_KEEP = "./data/tsv/keep.tsv"
        self.FILE_NAME_POPULARITY = "./data/labdata/article_pageview_full.tsv"
        self.FILE_NAME_NUMBERED_POPULARITY = "./data/tsv/popularity_with_id.tsv"
        self.FILE_NAME_NUMBERED_NORM_POPULARITY = "./data/tsv/normalized_popularity_with_id.tsv"
        self.FILE_NAME_SCALE_DENOMINATORS = "./data/labdata/scale_denominators.tsv"
        self.FILE_NAME_NUMBERED_ZOOM = "./data/tsv/numberedZoom.tsv"

        self.MAX_COORDINATE = 40                # Maximum x / y coords. Too large distorts.
        self.MAX_ZOOM = 20 # Maximum zoom level
        self.NUM_CLUSTERS = 15  # number of clusters to generate from K-means
        self.TSNE_THETA = 0.5  # lower values = more accurate maps, but take (much) longer
        self.TSNE_PCA_DIMENSIONS = None  # None indicates not to use PCA first
        self.PERCENTAGE_WATER = 0.05

        self.COLORWHEEL = {"#f19daa": {6: "#f19daa", 5: "#f2a6b2", 4: "#f3b0bb", 3: "#f5bac3", 2: "#f6c4cc", 1: "#f8ced4", 0: "#f9d7dd"},
                            "#26cf58": {6: "#26cf58", 5: "#3bd368", 4: "#51d879", 3: "#67dd8a", 2: "#7ce29a", 1: "#92e7ab", 0: "#a8ebbc"},
                            "#a51cd7": {6: "#a51cd7", 5: "#ae32db", 4: "#b749df", 3: "#c060e3", 2: "#c976e7", 1: "#d28deb", 0: "#dba4ef"},
                            "#70c946": {6: "#70c946", 5: "#7ece58", 4: "#8cd36a", 3: "#9ad97d", 2: "#a9de90", 1: "#b7e4a2", 0: "#c5e9b5"},
                            "#5346f1": {6: "#5346f1", 5: "#6458f2", 4: "#756af3", 3: "#867df5", 2: "#9790f6", 1: "#a9a2f8", 0: "#bab5f9"},
                            "#7da400": {6: "#7da400", 5: "#8aad19", 4: "#97b632", 3: "#a4bf4c", 2: "#b1c866", 1: "#bed17f", 0: "#cbda99"},
                            "#9561ff": {6: "#9561ff", 5: "#9f70ff", 4: "#aa80ff", 3: "#b490ff", 2: "#bfa0ff", 1: "#cab0ff", 0: "#d4bfff"},
                            "#00711b": {6: "#00711b", 5: "#197f31", 4: "#328d48", 3: "#4c9b5f", 2: "#66a976", 1: "#7fb88d", 0: "#99c6a3"},
                            "#fd5cff": {6: "#fd5cff", 5: "#fd6cff", 4: "#fd7cff", 3: "#fd8cff", 2: "#fd9dff", 1: "#feadff", 0: "#febdff"},
                            "#757b00": {6: "#757b00", 5: "#828819", 4: "#909532", 3: "#9ea24c", 2: "#acaf66", 1: "#babd7f", 0: "#c7ca99"},
                            "#6e76ff": {6: "#6e76ff", 5: "#7c83ff", 4: "#8b91ff", 3: "#999fff", 2: "#a8acff", 1: "#b6baff", 0: "#c5c8ff"},
                            "#da6500": {6: "#da6500", 5: "#dd7419", 4: "#e18332", 3: "#e5934c", 2: "#e8a266", 1: "#ecb27f", 0: "#f0c199"},
                            "#0048be": {6: "#0048be", 5: "#195ac4", 4: "#326ccb", 3: "#4c7ed1", 2: "#6691d8", 1: "#7fa3de", 0: "#99b5e5"},
                            "#ff6031": {6: "#ff6031", 5: "#ff6f45", 4: "#ff7f5a", 3: "#ff8f6e", 2: "#ff9f83", 1: "#ffaf98", 0: "#ffbfac"},
                            "#026fdc": {6: "#026fdc", 5: "#1b7ddf", 4: "#348be3", 3: "#4d9ae6", 2: "#67a8ea", 1: "#80b7ed", 0: "#99c5f1"},
                            "#c3000f": {6: "#c3000f", 5: "#c91926", 4: "#cf323e", 3: "#d54c57", 2: "#db666f", 1: "#e17f87", 0: "#e7999f"},
                            "#019577": {6: "#019577", 5: "#1a9f84", 4: "#33aa92", 3: "#4db49f", 2: "#66bfad", 1: "#80cabb", 0: "#99d4c8"},
                            "#ff33c7": {6: "#ff33c7", 5: "#ff47cc", 4: "#ff5bd2", 3: "#ff70d7", 2: "#ff84dd", 1: "#ff99e3", 0: "#ffade8"},
                            "#6bc789": {6: "#6bc789", 5: "#79cc94", 4: "#88d2a0", 3: "#97d7ac", 2: "#a6ddb8", 1: "#b5e3c4", 0: "#c3e8cf"},
                            "#af009b": {6: "#af009b", 5: "#b719a5", 4: "#bf32af", 3: "#c74cb9", 2: "#cf66c3", 1: "#d77fcd", 0: "#df99d7"},
                            "#686300": {6: "#686300", 5: "#777219", 4: "#868232", 3: "#95914c", 2: "#a4a166", 1: "#b3b17f", 0: "#c2c099"},
                            "#d081ff": {6: "#d081ff", 5: "#d48dff", 4: "#d99aff", 3: "#dea6ff", 2: "#e2b3ff", 1: "#e7c0ff", 0: "#ecccff"},
                            "#a4bc86": {6: "#a4bc86", 5: "#adc292", 4: "#b6c99e", 3: "#bfd0aa", 2: "#c8d6b6", 1: "#d1ddc2", 0: "#dae4ce"},
                            "#002084": {6: "#002084", 5: "#193690", 4: "#324c9c", 3: "#4c62a8", 2: "#6679b5", 1: "#7f8fc1", 0: "#99a5cd"},
                            "#ff8b55": {6: "#ff8b55", 5: "#ff9666", 4: "#ffa276", 3: "#ffad88", 2: "#ffb999", 1: "#ffc5aa", 0: "#ffd0bb"}}
        # ========== BorderFactory ==========
        self.MIN_NUM_IN_CLUSTER = 30  # eliminates noise
        self.BLUR_RADIUS = 5  # defines size of neighborhood for blurring
        self.MAX_ZOOM_SIMULATION = 18

        # ========== mapGenerator ==========
        self._localTiles = "./data/tiles/"
        self._serverTiles = "/var/www/html/tiles/"
        self.DIRECTORY_NAME_TILES = self._localTiles
        self.FILE_NAME_REGION_NAMES = "./data/labdata/top_categories_full.tsv"
        self.FILE_NAME_IMGNAME = "./data/images/world"
        self.FILE_NAME_IMGDOT = "./data/labdata/blackDot.png"
        self.FILE_NAME_COUNTRIES = "./data/geojson/countries.geojson"
        self.FILE_NAME_CONTOUR_DATA = "./data/geojson/contourData.geojson"
        self.FILE_NAME_MAP = "map.xml"
        self.FILE_NAME_REGION_CLUSTERS = "./data/tsv/region_clusters.tsv"
        self.FILE_NAME_REGION_BORDERS = "./data/tsv/region_borders.tsv"
        self.FILE_NAME_TOP_TITLES = "./data/geojson/top_100_articles.geojson"
        self.FILE_NAME_TITLES_BY_ZOOM = "./data/geojson/maxZoom_of_articles.geojson"


__config = Config()


def BAD_GET_CONFIG():
    """
        TODO: Remove all calls to this,
        replace with intiailization from a config file.
    """
    return __config
