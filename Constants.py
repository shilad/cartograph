 # ========== Analyzer ==========
FILE_NAME_WIKIBRAIN_VECS = "./data/vecs.tsv"
FILE_NAME_WIKIBRAIN_NAMES = "./data/names.tsv"
FILE_NAME_NAMES_AND_CLUSTERS = "./data/names_and_clusters.tsv"
FILE_NAME_COORDS_AND_CLUSTERS = "./data/coords_and_clusters.tsv"

NUM_CLUSTERS = 10  # number of clusters to generate from K-means
TSNE_THETA = 0.5  # lower values make more accurate maps, but takes (much) longer

# ========== BorderFactory ==========
SEARCH_RADIUS = 5  # acts as proxy for water level, lower  values leads to higher water
MIN_NUM_IN_CLUSTER = 10  # eliminates noise


# ========== mapGenerator ==========
DIRECTORY_NAME_TILES = "/var/www/html/tiles/"
FILE_NAME_REGION_NAMES = "./data/top_categories.tsv"
FILE_NAME_IMGNAME = "./data/world"
FILE_NAME_COUNTRIES = "./data/countries.geojson"
FILE_NAME_CONTOUR_DATA = "contourData.geojson"
FILE_NAME_MAP = "map.xml"

