import math
from pygsp import graphs, filters
import numpy as np
import Config
import Utils
import luigi
import Coordinates
from Regions import MakeRegions
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from collections import defaultdict

class DenoiserCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


class Denoise(MTimeMixin, luigi.Task):
    '''
    Remove outlier points and set water level for legibility in reading
    and more coherent contintent boundary lines
    '''
    def output(self):
        config = Config.get()
        if config.sampleBorders():
            return (
                TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                        "denoised_with_id")),
                TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                        "clusters_with_water")),
                TimestampedLocalTarget(config.getSample("GeneratedFiles",
                                                        "coordinates_with_water"))
            )
        else:
            return (
                TimestampedLocalTarget(config.get("GeneratedFiles",
                                                  "denoised_with_id")),
                TimestampedLocalTarget(config.get("GeneratedFiles",
                                                  "clusters_with_water")),
                TimestampedLocalTarget(config.get("GeneratedFiles",
                                                  "coordinates_with_water"))
            )

    def requires(self):
        if Config.get().sampleBorders():
            return (MakeRegions(),
                    Coordinates.CreateSampleCoordinates(),
                    DenoiserCode())
        else:
            return (MakeRegions(),
                    Coordinates.CreateFullCoordinates(),
                    DenoiserCode())

    def run(self):
        config = Config.get()
        if config.sampleBorders():

            coorPath = config.getSample("GeneratedFiles", "article_coordinates")
            clustersPath =  config.getSample("GeneratedFiles", "clusters_with_id")
        else:
            coorPath = config.get("GeneratedFiles", "article_coordinates")
            clustersPath =  config.get("GeneratedFiles", "clusters_with_id")


        coor = pd.read_table(coorPath)
        clusters = pd.read_table(clustersPath)
        feature = coor.merge(clusters, on='index')
        denoiser = Denoiser(feature, config.getint("PreprocessingConstants", "num_clusters"),
                            config.getfloat("PreprocessingConstants", "water_level"))

        results = denoiser.denoise()

        results[['index', 'keep']].to_csv(config.getSample("GeneratedFiles",
                                                           "denoised_with_id"), sep='\t', index=False,
                                          header=['index', 'keep'])
        results[['index', 'x', 'y']].to_csv(config.getSample("GeneratedFiles",
                                                             "coordinates_with_water"), sep='\t', index=False,
                                            header=['index', 'x', 'y'])
        results[['index', 'cluster']].to_csv(config.getSample("GeneratedFiles", "clusters_with_water"), sep='\t',
                                             header=['index', 'cluster'], index=False, )



def test_CreateContours():
    '''
    This tests the accuracy rate of the denoiser compared to a knn.
    It selects a random sample of articles from the output of denoiser, finds each article k nearest neighbors
    and counts how many of those neighbors belong to each cluster. Its is expected that
    each article would belong to the same cluster as the majority of its neighbors.
    If that is not the case the algorithm would tag that article as false (not to keep)

    It is expected that the knn results are be similar to the denoiser results. It compares the results of
    both algorithm and if they are close enough the test will pass
    :return:
    '''

    false_positve_threshold = 0.02
    false_negative_threshold = 0.4
    overall_accuracy_threshold = 0.90

    config = Config.initTest()

    # Create a unit test config object
    denoiser = Denoise()
    denoiser.run()
    df = read_files_for_test(config)

    #select ramdon sample from test files
    random_indices = np.random.permutation(df.index)
    test_cutoff = int(math.floor(df.shape[0] / 3))
    train = df.iloc[random_indices[test_cutoff:]]

    #create knn model from the set x, y coordinate for each article
    knn = NearestNeighbors(n_neighbors=11)
    knn.fit(df[['x', 'y']])

    neighborsCluster = defaultdict(dict)
    clusterForPoints = {}


    for row in train.itertuples():
        maxClusterCount = 0
        neis = knn.kneighbors([[row[3], row[4]]], return_distance=False) #find the neighbors for each article in our sample

        #assign to each article in the sample a cluster based on its neighbor cluster
        for neighbor in neis[0]:

            point = df.iloc[neighbor]

            if (not neighborsCluster[row[0]]):
                neighborsCluster[row[0]]
                clusterForPoints[row[0]] = 0

            if (point['cluster'] in neighborsCluster[row[0]]):
                neighborsCluster[row[0]][point['cluster']] += 1
            else:
                neighborsCluster[row[0]][point['cluster']] = 1

            currentCount = neighborsCluster[row[0]][point['cluster']]
            if (currentCount > maxClusterCount):
                maxClusterCount = currentCount
                clusterForPoints[row[0]] = point['cluster']

    #compare the expected cluster with the real cluster
    expected = []
    expected_index = []
    for key in clusterForPoints.keys():
        expected_index.append(key)
        if (clusterForPoints[key] != df.iloc[key]['cluster']):
            expected.append(False)
        else:
            expected.append(True)

    expected = pd.Series(expected, index=expected_index)
    true = train['keep']
    true = true

    #create confusion matrix that compare the expected result agains the denoiser results
    confusionMatrix = pd.crosstab(true, expected)
    print confusionMatrix

    false_negative_rate  = float(confusionMatrix[False].loc[True]) / float(
        confusionMatrix[False].loc[False] + confusionMatrix[False].loc[True])
    false_postive_rate = float(confusionMatrix[True].loc[False]) / float(
        confusionMatrix[True].loc[True] + confusionMatrix[True].loc[False])
    overall_accuracy_rate  = float(confusionMatrix[True].loc[True] + confusionMatrix[False].loc[False]) /\
                             float(confusionMatrix[False].loc[False] + confusionMatrix[False].loc[True] + confusionMatrix[True].loc[True] +
                confusionMatrix[True].loc[False])
    print "False negative: ", false_negative_rate
    print "False positive: ", false_postive_rate
    print "Overall accuracy", overall_accuracy_rate

    assert false_negative_rate < false_negative_threshold
    assert false_postive_rate < false_positve_threshold
    assert overall_accuracy_rate > overall_accuracy_threshold

    assert denoiser is not None

def read_files_for_test(config):
    keep = pd.read_table(config.getSample("GeneratedFiles",
                                             "denoised_with_id"))
    coors = pd.read_table(config.getSample("GeneratedFiles",
                                             "coordinates_with_water"))
    clusters = pd.read_table(config.getSample("GeneratedFiles", "clusters_with_water"))

    results = clusters.merge(coors, on='index')
    results = results.merge(keep, on='index')

    results.to_csv("./test_pandas/resultsDenoiseOri.tsv", sep='\t', header=['cluster', 'index', 'x', 'y', 'keep'])
    return results


class Denoiser:

    def __init__(self, featuresData, num_clusters, waterLevel):
        self.waterLevel = waterLevel
        self.num_clusters = num_clusters + 1  # total number of clusters + 1, which is the water cluster
        self.featuresData = self._add_water(featuresData)

        print('get here')
        print(self.waterLevel)
    def _make_filter(self, tau=10):
        '''
        Build graph and heatmap for denoising.
        '''
        graph = graphs.NNGraph(zip(self.featuresData['x'], self.featuresData['y']), k = self.num_clusters)


        graph.estimate_lmax()
        # higher tau, spikier signal, less points
        fn = filters.Heat(graph, tau=tau)
        return fn

    def _filter_in(self):
        '''
        Build matrix and do the filtering
        '''

        n = self.featuresData['x'].size
        filter_ = self._make_filter()
        signal = np.empty(self.num_clusters * n).reshape(self.num_clusters, n)
        vectors = np.zeros(n * self.num_clusters).reshape(n, self.num_clusters)

        for i, vec in enumerate(vectors):
            cluster_at_i = self.featuresData['cluster'][i]
            vec[cluster_at_i] = 1
        vectors = vectors.T
        for cluster_num, vec in enumerate(vectors):
            signal[cluster_num] = filter_.analysis(vec)
        return signal

    def _add_water(self, featuresData):

        maxV = featuresData['x'].abs().max()

        def f(n):
            return (np.random.beta(0.8, 0.8, n) - 0.5) * 2 * (maxV + 5)

        length = featuresData['x'].size
        water_x = f(int(length * self.waterLevel))
        water_y = f(int(length * self.waterLevel))
        index = ['w' + str(i) for i in range(len(water_x))]
        max_cluster = featuresData['cluster'].max()
        waterPoints = pd.DataFrame({'index': index ,'x': water_x, 'y': water_y, 'cluster': np.full(int(length * self.waterLevel),
                                                                                                   max_cluster + 1,
                                                                                                   dtype=np.int)})
        featuresData = featuresData.append(waterPoints, ignore_index = True )

        return featuresData


    def denoise(self):
        '''
        Return the denoised data
        '''
        signal = self._filter_in()
        max_idx_arr = np.argmax(signal, axis=0)
        keep = []
        count = 0
        for row in self.featuresData.itertuples():

            if max_idx_arr[count] == row[1]:
                keep.append(True)
            else:
                keep.append(False)
            count += 1
        self.featuresData['keep'] = keep

        #print(self.featuresData)
        return self.featuresData
