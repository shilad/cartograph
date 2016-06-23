import ConfigParser

class Config:
    def __init__(self):
        # ========== Analyzer ==========
        self.FILE_NAME_WIKIBRAIN_VECS = "./data/labdata/vecs.tsv"
        self.FILE_NAME_WIKIBRAIN_NAMES = "./data/labdata/names.tsv"
        self.FILE_NAME_NUMBERED_VECS = "./data/labdata/numberedVecs.tsv"
        self.FILE_NAME_NUMBERED_NAMES = "./data/labdata/numberedNames.tsv"
        self.FILE_NAME_ARTICLE_COORDINATES = "./data/labdata/tsne_cache.tsv"
        self.FILE_NAME_WATER_AND_ARTICLES = "./data/tsv/water_and_article_coordinates.tsv"
        self.FILE_NAME_WATER_CLUSTERS = "./data/tsv/clusters_with_water_pts.tsv"
        self.FILE_NAME_NUMBERED_CLUSTERS = "./data/tsv/numberedClusters.tsv"
        self.FILE_NAME_KEEP = "./data/tsv/keep.tsv"

        self.NUM_CLUSTERS = 10  # number of clusters to generate from K-means
        self.TSNE_THETA = 0.5  # lower values = more accurate maps, but take (much) longer
        self.TSNE_PCA_DIMENSIONS = None  # None indicates not to use PCA first
        self.PERCENTAGE_WATER = 0.1

        # ========== BorderFactory ==========
        self.SEARCH_RADIUS = 50  # proxy for water level, lower values = higher water
        self.REGION_BORDER_SIZE = 2
        self.MIN_NUM_IN_CLUSTER = 30  # eliminates noise

        # ========== mapGenerator ==========
        self._localTiles = "./data/tiles/"
        self._serverTiles = "/var/www/html/tiles/"
        self.DIRECTORY_NAME_TILES = self._localTiles
        self.FILE_NAME_REGION_NAMES = "./data/labdata/top_categories.tsv"
        self.FILE_NAME_IMGNAME = "./data/images/world"
        self.FILE_NAME_COUNTRIES = "./data/geojson/countries.geojson"
        self.FILE_NAME_CONTOUR_DATA = "./data/geojson/contourData.geojson"
        self.FILE_NAME_MAP = "Map.xml"
        self.FILE_NAME_REGION_CLUSTERS = "./data/tsv/region_clusters.tsv"
        self.FILE_NAME_REGION_BORDERS = "./data/tsv/region_borders.tsv"


__config = Config()


def BAD_GET_CONFIG():
    """
        TODO: Remove all calls to this, replace with intiailization from a config file.
    """
    return __config


    
