import luigi

# This needs to happen IMMEDIATELY to turn on headless rendering.
import matplotlib
matplotlib.use('Agg')
import cartograph
import os
import logging

from cartograph import FastKnn
from cartograph import Config
from cartograph import Colors
from cartograph import Util
from cartograph import Contour
from cartograph import Denoiser
from cartograph import MapStyler
from cartograph.BorderFactory.BorderBuilder import BorderBuilder
from cartograph.BorderFactory import BorderProcessor, Noiser, Vertex, VoronoiWrapper
from cartograph.BorderGeoJSONWriter import BorderGeoJSONWriter
from cartograph.TopTitlesGeoJSONWriter import TopTitlesGeoJSONWriter
from cartograph.ZoomGeoJSONWriter import ZoomGeoJSONWriter
from cartograph.ZoomTSVWriter import ZoomTSVWriter
from cartograph.Labels import Labels
from cartograph.Config import initConf
from cartograph.CalculateZooms import CalculateZooms
from cartograph.Interpolater import Interpolater
from cartograph.PopularityLabelSizer import PopularityLabelSizer
from collections import defaultdict
from tsne import bh_sne
from time import time
import numpy as np
from sklearn.cluster import KMeans
from cartograph.LuigiUtils import LoadGeoJsonTask, TimestampedPostgresTarget, TimestampedLocalTarget, MTimeMixin


logger = logging.getLogger('workload')
logger.setLevel(logging.INFO)

config, COLORWHEEL = initConf("conf.txt")
RUN_TIME = time()


# ====================================================================
# Read in codebase as external dependencies to automate a rerun of any
# code changed without having to do a manual invalidation
# NOTE: Any new .py files that will run *must* go here for automation
# ====================================================================

class ContourCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Contour.__file__))

class ColorsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Colors.__file__))


class DenoiserCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Denoiser.__file__))


class MapStylerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.MapStyler.__file__))


class BorderFactoryCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.BorderFactory.BorderBuilder.__file__),
                TimestampedLocalTarget(cartograph.BorderFactory.BorderProcessor.__file__),
                TimestampedLocalTarget(cartograph.BorderFactory.Noiser.__file__),
                TimestampedLocalTarget(cartograph.BorderFactory.Vertex.__file__),
                TimestampedLocalTarget(cartograph.BorderFactory.VoronoiWrapper.__file__))


class BorderGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.BorderGeoJSONWriter.__file__))


class TopTitlesGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.TopTitlesGeoJSONWriter.__file__))


class LabelsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.Labels.__file__))


class CalculateZoomsCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.CalculateZooms.__file__))


class ZoomGeoJSONWriterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(cartograph.ZoomGeoJSONWriter.__file__))

class PGLoaderCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(cartograph.LuigiUtils.__file__))


class InterpolaterCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(cartograph.Interpolater.__file__))

class PopularityLabelSizerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(cartograph.PopularityLabelSizer.__file__))


# ====================================================================
# Clean up raw wikibrain data for uniform data structure manipulation
# ====================================================================


class LabelNames(luigi.ExternalTask):
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''
    def output(self):
        return (TimestampedLocalTarget(config.get("ExternalFiles", "region_names")))

    def requires(self):
        return EnsureDirectoriesExist() # This should occur in at least one of the sample tasks


class ArticlePopularity(luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(config.get("ExternalFiles", "popularity")))


class WikiBrainNumbering(MTimeMixin, luigi.ExternalTask):
    '''
    Number the name and vector output of WikiBrain files so that each
    article has a unique id corrosponding to all of its data for future
    use of any subset of features of interest
    '''

    def output(self):
        return (TimestampedLocalTarget(config.get("ExternalFiles",
                                             "vecs_with_id")),
                TimestampedLocalTarget(config.get("ExternalFiles",
                                             "names_with_id")))

class EnsureDirectoriesExist(luigi.Task):
    def __init__(self, *args, **kwargs):
        super(EnsureDirectoriesExist, self).__init__(*args, **kwargs)
        self.configKeys = ('baseDir', 'externalDir', 'generatedDir', 'geojsonDir')

    def output(self):
        return list(
            luigi.LocalTarget(config.get('DEFAULT', n)) for n in self.configKeys
        )

    def requires(self): return []

    def run(self):
        for k in self.configKeys:
            fn = config.get('DEFAULT', k)
            if not os.path.isdir(fn): os.makedirs(fn)


def getSampleIds(n=None):
    if n is None:
        n = config.getint('PreprocessingConstants', 'sample_size')
    pops = Util.read_features(config.get("PostprocessingFiles", "popularity_with_id"))
    tuples = list((pops[id]['popularity'], id) for id in pops)
    tuples.sort()
    return set(id for (pop, id) in tuples[-n:])


class SampleCreator(MTimeMixin, luigi.Task):
    path = luigi.Parameter()

    def requires(self):
        return (
            WikiBrainNumbering(),
            PopularityIdentifier(),
            EnsureDirectoriesExist()
        )

    def samplePath(self):
        n = config.getint('PreprocessingConstants', 'sample_size')
        return Config.samplePath(self.path, n)

    def output(self):
        return TimestampedLocalTarget(self.samplePath())

    def run(self):
        sampleIds = getSampleIds()
        with open(self.path, 'r') as input, open(self.samplePath(), 'w') as output:
            header = input.readline()
            output.write(header + '\n')
            for line in input:
                id = line.split('\t')[0]
                if id in sampleIds:
                    output.write(line + '\n')


# ====================================================================
# Data Training and Analysis Stage
# ====================================================================


class PopularityIdentifier(MTimeMixin, luigi.Task):
    '''
    Generate a tsv that matches Wikibrain popularity count to a unique
    article ID for later compatibility with Util.read_features()
    '''
    def requires(self):
        return (WikiBrainNumbering(),
                ArticlePopularity())

    def output(self):
        return (TimestampedLocalTarget(config.get("PreprocessingFiles",
                                                 "popularity_with_id")))

    def run(self):
        featureDict = Util.read_features(config.get("ExternalFiles",
                                                    "names_with_id"))
        idList = list(featureDict.keys())

        nameDict = {}
        with open(config.get("ExternalFiles", "popularity")) as popularity:
            lines = popularity.readlines()
            for line in lines:
                lineAr = line.split("\t")
                name = lineAr[0]
                pop = lineAr[1][:-1]
                nameDict[name] = pop

        popularityList = []
        for featureID in idList:
            name = featureDict[featureID]["name"]
            popularityList.append(nameDict[name])

        Util.write_tsv(config.get('PreprocessingFiles', 'popularity_with_id'),
                       ("id", "popularity"),
                       idList, popularityList)


class PercentilePopularityIdentifier(MTimeMixin, luigi.Task):
    '''
    Bins the popularity values by given percentiles then maps the values to
    the unique article ID.
    '''
    def requires(self):
        return (PopularityIdentifier(),
                InterpolateNewPoints(),
                PopularityLabelSizerCode())

    def output(self):
        return (TimestampedLocalTarget(config.get("PreprocessingFiles",
                                             "percentile_popularity_with_id")))

    def run(self):
        readPopularData = Util.read_tsv(config.get("PreprocessingFiles",
                                                   "popularity_with_id"))
        popularity = list(map(float, readPopularData['popularity']))
        index = list(map(int, readPopularData['id']))

        popLabel = PopularityLabelSizer(config.getint("MapConstants", "num_pop_bins"),
                                                    popularity)
        popLabelScores = popLabel.calculatePopScore()

        Util.write_tsv(config.get("PreprocessingFiles", "percentile_popularity_with_id"),
                                    ("id", "popBinScore"), index, popLabelScores)


class MakeSampleRegions(MTimeMixin, luigi.Task):
    '''
    Run KMeans to cluster article points into specific continents.
    Seed is set at 42 to make sure that when run against labeling
    algorithm clusters numbers consistently refer to the same entity
    '''
    def output(self):
        return TimestampedLocalTarget(config.getSample("PreprocessingFiles",
                                            "clusters_with_id"))

    def requires(self):
        return (
            CreateSampleCoordinates(), 
            SampleCreator(config.get("ExternalFiles", "vecs_with_id"))
        )

    def run(self):
        featureDict = Util.read_features(config.getSample("ExternalFiles",
                                                    "vecs_with_id"))
        keys = list(k for k in featureDict.keys() if len(featureDict[k]['vector']) > 0)
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        labels = list(KMeans(config.getint("PreprocessingConstants",
                                           "num_clusters"),
                             random_state=42).fit(vectors).labels_)

        Util.write_tsv(config.getSample("PreprocessingFiles", "clusters_with_id"),
                       ("index", "cluster"), keys, labels)


class MakeRegions(MTimeMixin, luigi.Task):
    def output(self):
        return TimestampedLocalTarget(config.get("PreprocessingFiles", "clusters_with_id"))

    def requires(self):
        return (
            MakeSampleRegions(), 
            WikiBrainNumbering(), 
            CreateSampleAnnoyIndex()
        )

    def run(self):
        sampleRegions = Util.read_features(config.getSample("PreprocessingFiles", "clusters_with_id"),)
        vecs = Util.read_features(config.get("ExternalFiles", "vecs_with_id"))
        knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
        assert(knn.exists())
        knn.read()
        ids = []
        clusters = []
        for i, (id, row) in enumerate(vecs.items()):
            if i % 10000 == 0:
                logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
            sums = defaultdict(float)
            if len(row['vector']) == 0: continue
            hood = knn.neighbors(row['vector'], 5)
            if not hood: continue
            for (id, score) in hood:
                c = sampleRegions[id].get('cluster')
                if c is not None:
                    sums[c] += score
            cluster = max(sums, key=sums.get)
            ids.append(id)
            clusters.append(cluster)
            
        Util.write_tsv(config.get("PreprocessingFiles", "clusters_with_id"),
                       ("index", "cluster"), ids, clusters)


class CreateEmbedding(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes
    '''
    def output(self):
        return TimestampedLocalTarget(config.getSample("ExternalFiles",
                                            "article_embedding"))

    def requires(self):
        return (
            WikiBrainNumbering(),
            SampleCreator(config.get("ExternalFiles", "vecs_with_id"))
        )

    def run(self):
        # Create the embedding.
        featureDict = Util.read_features(config.getSample("ExternalFiles",
                                                          "vecs_with_id"),
                                         id_set=getSample())
        keys = list(featureDict.keys())
        vectors = np.array([featureDict[vID]["vector"] for vID in keys])
        out = bh_sne(vectors,
                     pca_d=None,
                     theta=config.getfloat("PreprocessingConstants", "tsne_theta"))
        X, Y = list(out[:, 0]), list(out[:, 1])
        Util.write_tsv(config.getSample("ExternalFiles", "article_embedding"),
                       ("index", "x", "y"), keys, X, Y)

class CreateFullAnnoyIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        super(CreateFullAnnoyIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.get("ExternalFiles", "vecs_with_id")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        return WikiBrainNumbering()

    def output(self):
        return TimestampedLocalTarget(self.knn.pathAnnoy), TimestampedLocalTarget(self.knn.pathIds)

    def run(self):
        self.knn.rebuild()


class CreateSampleAnnoyIndex(MTimeMixin, luigi.Task):
    def __init__(self, *args, **kwargs):
        super(CreateSampleAnnoyIndex, self).__init__(*args, **kwargs)
        self.vecPath = config.getSample("ExternalFiles", "vecs_with_id")
        self.knn = FastKnn.FastKnn(self.vecPath)

    def requires(self):
        return WikiBrainNumbering(), SampleCreator(config.get("ExternalFiles", "vecs_with_id"))

    def output(self):
        return TimestampedLocalTarget(self.knn.pathAnnoy), TimestampedLocalTarget(self.knn.pathIds)

    def run(self):
        self.knn.rebuild()


class CreateSampleCoordinates(MTimeMixin, luigi.Task):
    '''
    Use TSNE to reduce high dimensional vectors to x, y coordinates for
    mapping purposes.
    '''
    def output(self):
        return TimestampedLocalTarget(config.getSample("PreprocessingFiles",
                                            "article_coordinates"))

    def requires(self):
        return CreateEmbedding(), CreateSampleAnnoyIndex()

    def run(self):

        # Rescale sampled embedded points
        points = Util.read_features(config.getSample("ExternalFiles",
                                               "article_embedding"))
        keys = list(points.keys())
        X = [float(points[k]['x']) for k in keys]
        Y = [float(points[k]['y']) for k in keys]
        maxVal = max(abs(v) for v in X + Y)
        scaling = config.getint("MapConstants", "max_coordinate") / maxVal
        X = [x * scaling for x in X]
        Y = [y * scaling for y in Y]

        Util.write_tsv(config.getSample("PreprocessingFiles",
                                  "article_coordinates"),
                       ("index", "x", "y"), keys, X, Y)


class CreateFullCoordinates(MTimeMixin, luigi.Task):
    def output(self):
        return TimestampedLocalTarget(config.get("PreprocessingFiles", "article_coordinates"))

    def requires(self):
        return CreateSampleCoordinates(), WikiBrainNumbering(), CreateSampleAnnoyIndex()

    def run(self):
        sampleCoords = Util.read_features(config.getSample("PreprocessingFiles", "article_coordinates"))
        vecs = Util.read_features(config.get("ExternalFiles", "vecs_with_id"))
        knn = FastKnn.FastKnn(config.getSample("ExternalFiles", "vecs_with_id"))
        assert(knn.exists())
        knn.read()
        ids = []
        X = []
        Y = []
        for i, (id, row) in enumerate(vecs.items()):
            if i % 10000 == 0:
                logger.info('interpolating coordinates for point %d of %d' % (i, len(vecs)))
            xSums = 0.0
            ySums = 0.0
            scoreSums = 0.0
            if len(row['vector']) == 0: continue
            hood = knn.neighbors(row['vector'], 5)
            for (id, score) in hood:
                xSums += score * float(sampleCoords[id]['x'])
                ySums += score * float(sampleCoords[id]['y'])
                scoreSums += score
            X.append(xSums / scoreSums)
            Y.append(ySums / scoreSums)
            ids.append(id)
            
        Util.write_tsv(config.get("PreprocessingFiles",
                                  "article_coordinates"),
                       ("index", "x", "y"), ids, X, Y)

class ZoomLabeler(MTimeMixin, luigi.Task):
    '''
    Calculates a starting zoom level for every article point in the data,
    i.e. determines when each article label should appear.
    '''
    def output(self):
        return TimestampedLocalTarget(config.get("PreprocessingFiles",
                                                 "zoom_with_id"))

    def requires(self):
        return (MakeRegions(),
                CalculateZoomsCode(),
                CreateCoordinates(),
                PopularityIdentifier())

    def run(self):
        feats = Util.read_features(config.get("PreprocessingFiles",
                                              "popularity_with_id"),
                                   config.get("PreprocessingFiles",
                                              "article_coordinates"),
                                   config.get("PreprocessingFiles",
                                              "clusters_with_id"))

        zoom = CalculateZooms(feats,
                              config.getint("MapConstants", "max_coordinate"),
                              config.getint("PreprocessingConstants", "num_clusters"))
        numberedZoomDict = zoom.simulateZoom(config.getint("MapConstants", "max_zoom"),
                                             config.getint("MapConstants", "first_zoom_label"))

        keys = list(numberedZoomDict.keys())
        zoomValue = list(numberedZoomDict.values())


        Util.write_tsv(config.get("PreprocessingFiles", "zoom_with_id"),
                       ("index", "maxZoom"), keys, zoomValue)


class Denoise(MTimeMixin, luigi.Task):
    '''
    Remove outlier points and set water level for legibility in reading
    and more coherent contintent boundary lines
    '''
    def output(self):
        return (
            TimestampedLocalTarget(config.getSample("PreprocessingFiles",
                                         "denoised_with_id")),
            TimestampedLocalTarget(config.getSample("PreprocessingFiles",
                                         "clusters_with_water")),
            TimestampedLocalTarget(config.getSample("PreprocessingFiles",
                                         "coordinates_with_water"))
        )

    def requires(self):
        return (MakeRegions(),
                CreateSampleCoordinates(),
                DenoiserCode())

    def run(self):
        featureDict = Util.read_features(config.getSample("PreprocessingFiles",
                                                    "article_coordinates"),
                                         config.getSample("PreprocessingFiles",
                                                    "clusters_with_id"))
        featureIDs = list(featureDict.keys())
        x = [float(featureDict[fID]["x"]) for fID in featureIDs]
        y = [float(featureDict[fID]["y"]) for fID in featureIDs]
        c = [int(featureDict[fID]["cluster"]) for fID in featureIDs]

        denoiser = Denoiser.Denoiser(x, y, c,
                                     config.getfloat("PreprocessingConstants",
                                                     "water_level"))
        keepBooleans, waterX, waterY, waterCluster = denoiser.denoise()

        for x in range(len(waterX) - len(featureIDs)):
            featureIDs.append("w" + str(x))

        Util.write_tsv(config.getSample("PreprocessingFiles",
                                  "denoised_with_id"),
                       ("index", "keep"),
                       featureIDs, keepBooleans)

        Util.write_tsv(config.getSample("PreprocessingFiles",
                                  "coordinates_with_water"),
                       ("index", "x", "y"), featureIDs, waterX, waterY)
        Util.write_tsv(config.getSample("PreprocessingFiles", "clusters_with_water"),
                       ("index", "cluster"), featureIDs, waterCluster)


# ====================================================================
# Map File and Image (for visual check) Stage
# ====================================================================


class CreateContinents(MTimeMixin, luigi.Task):
    '''
    Use BorderFactory to define edges of continent polygons based on
    voronoi tesselations of both article and waterpoints storing
    article clusters as the points of their exterior edge
    '''
    def output(self):
        return (
            TimestampedLocalTarget(config.get("MapData", "countries_geojson")),
            TimestampedLocalTarget(config.get("PreprocessingFiles", "country_borders")),
            TimestampedLocalTarget(config.get("MapData", "clusters_with_region_id")),
            TimestampedLocalTarget(config.get("MapData", "borders_with_region_id")))

    def requires(self):
        return (LabelNames(),
                CreateSampleCoordinates(),
                BorderGeoJSONWriterCode(),
                BorderFactoryCode(),
                MakeSampleRegions(),
                Denoise())

    def decomposeBorders(self, clusterDict):
        '''
        Break down clusters into every region that comprises the whole
        and save for later possible data manipulation
        TODO: Extract interior ports as well as borders
        '''
        regionList = []
        membershipList = []
        for key in clusterDict:
            regions = clusterDict[key]
            for region in regions:
                regionList.append(region)
                membershipList.append(key)
        return regionList, membershipList

    def run(self):
        clusterDict = BorderBuilder(config).build()
        clustList = [list(clusterDict[x]) for x in list(clusterDict.keys())]
        regionList, membershipList = self.decomposeBorders(clusterDict)
        regionFile = config.get("ExternalFiles", "region_names")
        BorderGeoJSONWriter(clustList, regionFile).writeToFile(config.get("MapData", "countries_geojson"))
        Util.write_tsv(config.get("MapData", "clusters_with_region_id"),
                       ("region_id", "cluster_id"),
                       range(1, len(membershipList) + 1),
                       membershipList)
        Util.write_tsv(config.get("MapData", "borders_with_region_id"),
                       ("region_id", "border_list"),
                       range(1, len(regionList) + 1),
                       regionList)
        Util.write_tsv(config.get("PreprocessingFiles", "country_borders"),
                       ("cluster_id", "border_list"),
                       range(len(clustList)),
                       clustList)


class CreateContours(MTimeMixin, luigi.Task):
    '''
    Make contours based on density of points inside the map
    Generated as geojson data for later use inside map.xml
    '''
    def requires(self):
        return (CreateSampleCoordinates(),
                SampleCreator(config.get("ExternalFiles", "vecs_with_id")),
                ContourCode(),
                CreateContinents())

    def output(self):
        return TimestampedLocalTarget(config.get("MapData", "centroid_contours_geojson"))

    def run(self):
        featuresDict = Util.read_features(config.getSample("PreprocessingFiles",
                                                     "article_coordinates"),
                                          config.getSample("PreprocessingFiles",
                                                     "clusters_with_id"),
                                          config.getSample("PreprocessingFiles",
                                                     "denoised_with_id"),
                                          config.getSample("ExternalFiles",
                                                     "vecs_with_id"))
        for key in featuresDict.keys():
            if key[0] == "w":
                del featuresDict[key]

        numClusters = config.getint("PreprocessingConstants", "num_clusters")
        numContours = config.getint('PreprocessingConstants', 'num_contours')
        writeFile = config.get("MapData", "countries_geojson")

        contour = Contour.ContourCreator(numClusters)
        contour.buildContours(featuresDict, writeFile)
        contour.makeDensityContourFeatureCollection(config.get("MapData", "density_contours_geojson"))
        contour.makeCentroidContourFeatureCollection(config.get("MapData", "centroid_contours_geojson"))


class CreateStates(MTimeMixin, luigi.Task):
    '''
    Create states within regions
    '''
    def requires(self):
        return(Denoise(),
               CreateContinents(),
               CreateContours())
    def output(self):
        ''' TODO - figure out what this is going to return'''
        return TimestampedLocalTarget(config.FILE_NAME_STATE_CLUSTERS)
    def run(self):
        #create dictionary of article ids to a dictionary with cluster numbers and vectors representing them
        articleDict = Util.read_features(config.FILE_NAME_NUMBERED_CLUSTERS, config.FILE_NAME_NUMBERED_VECS)

        #loop through and grab all the points (dictionaries) in each cluster that match the current cluster number (i), write the keys to a list
        for i in range(0, config.NUM_CLUSTERS):
            keys = []
            for article in articleDict:
                if int(articleDict[article]['cluster']) == i:
                    keys.append(article)
            #grab those articles' vectors from articleDict (thank you @ brooke for read_features, it is everything)
            vectors = np.array([articleDict[vID]['vector'] for vID in keys])

            #cluster vectors
            preStateLabels = list(KMeans(6,
                             random_state=42).fit(vectors).labels_)
            #append cluster number to cluster so that sub-clusters are of the form [larger][smaller] - eg cluster 4 has subclusters 40, 41, 42
            stateLabels = []
            for label in preStateLabels:
                newlabel = str(i) + str(label)
                stateLabels.append(newlabel)

            #also need to make a new utils method for append_tsv rather than write_tsv
            Util.append_tsv(config.FILE_NAME_STATE_CLUSTERS,
                       ("index", "stateCluster"), keys, stateLabels)
        #CODE THUS FAR CREATES ALL SUBCLUSTERS, NOW YOU JUST HAVE TO FIGURE OUT HOW TO INTEGRATE THEM

        #ALSO HOW TO DETERMINE THE BEST # OF CLUSTERS FOR EACH SUBCLUSTER??? IT SEEMS LIKE THEY SHOULD VARY (MAYBE BASED ON # OF POINTS?)


        #then make sure those get borders created for them??
        #then create and color those polygons in xml

class CreateLabelsFromZoom(MTimeMixin, luigi.Task):
    '''
    Generates geojson data for relative zoom labelling in map.xml
    '''
    def output(self):
        return TimestampedLocalTarget(config.get("MapData", "title_by_zoom"))

    def requires(self):
        return (
                ZoomLabeler(),
                PercentilePopularityIdentifier(),
                ZoomGeoJSONWriterCode(),
         )


    def run(self):
        featureDict = Util.read_features(
            config.get("PreprocessingFiles", "zoom_with_id"),
            config.get("PreprocessingFiles", "article_coordinates"),
            config.get("PreprocessingFiles", "popularity_with_id"),
            config.get("PreprocessingFiles", "names_with_id"),
            config.get("PreprocessingFiles", "percentile_popularity_with_id"))

        titlesByZoom = ZoomGeoJSONWriter(featureDict)
        titlesByZoom.generateZoomJSONFeature(config.get("MapData", "title_by_zoom"))



class CreateTopLabels(MTimeMixin, luigi.Task):
    '''
    Write the top 100 most popular articles to file for relative zoom
    Generated as geojson data for use inside map.xml
    '''
    def requires(self):
        return (PopularityIdentifier(),
                CreateCoordinates(),
                MakeRegions(),
                TopTitlesGeoJSONWriterCode())

    def output(self):
        return TimestampedLocalTarget(config.get("MapData", "top_titles"))

    def run(self):
        titleLabels = TopTitlesGeoJSONWriter(9000)
        titleLabels.generateJSONFeature(config.get("MapData", "top_titles"))

class LoadContours(LoadGeoJsonTask):
    def __init__(self):
        LoadGeoJsonTask.__init__(self,
            config,
            'contours',
            config.get('MapData', 'centroid_contours_geojson')
        )

    def requires(self):
        return CreateContours(), PGLoaderCode()


class LoadCoordinates(LoadGeoJsonTask):
    def __init__(self):
        LoadGeoJsonTask.__init__(self,
            config,
            'coordinates',
            config.get('MapData', 'title_by_zoom')
        )

    def requires(self):
        return CreateCoordinates(), PGLoaderCode(), CreateLabelsFromZoom()


class LoadCountries(LoadGeoJsonTask):
    def __init__(self):
        LoadGeoJsonTask.__init__(self,
            config, 'countries',
            config.get('MapData', 'countries_geojson')
        )

    def requires(self):
        return CreateContinents(), PGLoaderCode()


class CreateMapXml(MTimeMixin, luigi.Task):
    '''
    Creates the mapnik map.xml configuration file and renders png and svg
    images of the map for visual reference to make sure code excuted properly.
    Map png and svg can be found in ./data/images
    '''
    def output(self):
        return (
            TimestampedLocalTarget(config.get("MapOutput", "map_file")))

    def requires(self):
        return (

            LoadContours(),
            LoadCoordinates(),
            LoadCountries(),
            MapStylerCode(),
            ColorsCode()
        )

    def run(self):
        regionClusters = Util.read_features(config.get("MapData", "clusters_with_region_id"))
        regionIds = sorted(set(int(region['cluster_id']) for region in regionClusters.values()))
        regionIds = map(str, regionIds)
        countryBorders = Util.read_features(config.get("PreprocessingFiles", "country_borders"))
        colorFactory = Colors.ColorSelector(countryBorders, COLORWHEEL)
        colors = colorFactory.optimalColoring()
        ms = MapStyler.MapStyler(config, colors)
        mapfile = config.get("MapOutput", "map_file")
        imgfile = config.get("MapOutput", "img_src_name")

        ms.makeMap(config.get("MapData", "centroid_contours_geojson"),
                   config.get("MapData", "countries_geojson"),
                   regionIds)
        ms.saveMapXml(config.get("MapData", "countries_geojson"),
                      mapfile)
        ms.saveImage(mapfile, imgfile + ".png")
        ms.saveImage(mapfile, imgfile + ".svg")


class LabelMapUsingZoom(MTimeMixin, luigi.Task):
    '''
    Adding the labels directly into the xml file for map rendering.
    Labels are added to appear based on a grid based zoom calculation in
    the CalculateZooms.py
    '''
    def output(self):
        return (TimestampedLocalTarget(config.get("MapOutput", "map_file")))

    def requires(self):
        return (CreateMapXml(),
                CreateLabelsFromZoom(),
                CreateContinents(),
                LabelsCode(),
                CalculateZoomsCode(),
                ZoomGeoJSONWriterCode()
                )

    def run(self):
        labelClust = Labels(config, config.get("MapOutput", "map_file"),
                            'countries', config.get("MapData", "scale_dimensions"))
        maxScaleClust = labelClust.getMaxDenominator(0)
        minScaleClust = labelClust.getMinDenominator(5)


        labelClust.writeLabelsXml('[labels]', 'interior',
                                  breakZoom=config.getint('MapConstants', 'first_zoom_label'),
                                  minScale=10,
                                  maxScale=0)
        # zoomValues = set()
        # zoomValueData = Util.read_features(config.get("PreprocessingFiles",
        #                                               "zoom_with_id"))
        # for zoomInfo in list(zoomValueData.values()):
        #     zoomValues.add(zoomInfo['maxZoom'])

        labelCities = Labels(config, config.get("MapOutput", "map_file"),
                             'coordinates', config.get("MapData", "scale_dimensions"))
        labelCities.writeLabelsByZoomToXml('[citylabel]', 'point',
                                           config.getint("MapConstants", "max_zoom"),
                                           imgFile=config.get("MapResources",
                                                              "img_dot"),
                                           numBins=config.getint("MapConstants",
                                                                "num_pop_bins"))


class RenderMap(MTimeMixin, luigi.Task):
    '''
    Write the final product xml of all our data manipulations to an image file
    to ensure that everything excuted as it should
    '''
    def requires(self):
        return (CreateMapXml(),
                LoadCoordinates(),
                LoadCountries(),
                LoadContours(),
                LabelMapUsingZoom(),
                MapStylerCode(),
                ColorsCode())

    def output(self):
        return(
            TimestampedLocalTarget(config.get("MapOutput",
                                         "img_src_name") + '.png'),
            TimestampedLocalTarget(config.get("MapOutput",
                                         "img_src_name") + '.svg'))

    def run(self):
        countryBorders = Util.read_features(config.get("PreprocessingFiles", "country_borders"))
        colorFactory = Colors.ColorSelector(countryBorders, COLORWHEEL)
        colors = colorFactory.optimalColoring()
        ms = MapStyler.MapStyler(config, colors)
        ms = MapStyler.MapStyler(config, COLORWHEEL)
        ms.saveImage(config.get("MapOutput", "map_file"),
                     config.get("MapOutput", "img_src_name") + ".png")
        ms.saveImage(config.get("MapOutput", "map_file"),
                     config.get("MapOutput", "img_src_name") + ".svg")
