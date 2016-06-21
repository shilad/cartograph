# ========== Analyzer ==========
FILE_NAME_WIKIBRAIN_VECS = "./data/tsv/vecs.tsv"
FILE_NAME_WIKIBRAIN_NAMES = "./data/tsv/names.tsv"
FILE_NAME_NUMBERED_VECS = "./data/tsv/numberedVecs.tsv"
FILE_NAME_NUMBERED_NAMES = "./data/tsv/numberedNames.tsv"
FILE_NAME_ARTICLE_COORDINATES = "./data/tsv/tsne_cache.tsv"
FILE_NAME_NUMBERED_CLUSTERS = "./data/tsv/nlClusters.tsv"
FILE_NAME_KEEP = "./data/tsv/keep.tsv"


NUM_CLUSTERS = 10  # number of clusters to generate from K-means
TSNE_THETA = 0.5  # lower values = more accurate maps, but take (much) longer
TSNE_PCA_DIMENSIONS = None  # None indicates not to use PCA first
PERCENTAGE_WATER = 0.1


# ========== BorderFactory ==========
SEARCH_RADIUS = 50  # proxy for water level, lower values = higher water
REGION_BORDER_SIZE = 2
MIN_NUM_IN_CLUSTER = 30  # eliminates noise


# ========== mapGenerator ==========
_localTiles = "./data/tiles/"
_serverTiles = "/var/www/html/tiles/"
DIRECTORY_NAME_TILES = _serverTiles
FILE_NAME_REGION_NAMES = "./data/tsv/top_categories.tsv"
FILE_NAME_IMGNAME = "./data/images/world"
FILE_NAME_COUNTRIES = "./data/geojson/countries.geojson"
FILE_NAME_CONTOUR_DATA = "./data/geojson/contourData.geojson"
FILE_NAME_MAP = "map.xml"
