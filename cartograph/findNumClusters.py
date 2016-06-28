import numpy as np
from sklearn.cluster import KMeans
from scipy import spatial
import Util


class findNumClusters():
    def __init__(self, dataSet, maxClusters):
        self.data = dataSet
        self.maxClusters = maxClusters
        self.difference = []
        self.labels = []
        self.gain = {}

    def kMeans(self):
        for numClusters in range(1, self.maxClusters + 1):
            print "Running on %s clusters" % (numClusters)
            self.labels = list(KMeans(numClusters,
                          random_state=42).fit(np.array(self.data)).labels_)
            centroids = [[0 for x in range(len(self.data[0]))]
                         for y in range(numClusters)]
            for index, pt in enumerate(self.data):
                cluster = self.labels[index]
                prevCenter = centroids[cluster]
                centroids[cluster] = self._solve_centroid(pt, prevCenter)

            self.gain[numClusters]["cosine"] = [0 for x in range(numClusters + 1)]
            self.gain[numClusters]["cheby"] = [0 for x in range(numClusters + 1)]
            self.gain[numClusters]["euclid"] = [0 for x in range(numClusters + 1)]
            self.gain[numClusters]["jaccard"] = [0 for x in range(numClusters + 1)]
            for index, pt in enumerate(self.data):
                cluster = self.labels[index]
                centroid = centroids[cluster]
                self.gain[numClusters]["cosine"][cluster] += spatial.distance.cosine(centroid, pt)
                self.gain[numClusters]["cheby"][cluster] += spatial.distance.chebyshev(centroid, pt)
                self.gain[numClusters]["euclid"][cluster] += spatial.distance.sqeuclidean(centroid, pt)
                self.gain[numClusters]["jaccard"][cluster] += spatial.distance.jaccard(centroid, pt)

            if self._bestMarginalGain(numClusters, centroids) is False:
                return numClusters, self.labels

        print "Max clusters is best marginal gain," + \
              "consider rerunning with higher max"
        return maxClusters, self.labels

    def _solve_centroid(self, vec1, vec2):
        if len(vec1) != len(vec2):
            print "Not equal vectors"
            raise IndexError
        centroid = []
        for index, val in enumerate(vec1):
            avg = (val + vec2[index]) / 2
            centroid.append(avg)

        return centroid

    def _bestMarginalGain(self, numClusters, labels):
        keys = self.gain.keys()
        avgList = [self.gain[key]["avg"] for key in keys]

        self.gain[numClusters]["avg"] = 0
        distMetrics = list(self.gain[numClusters].values())
        for val in distMetrics:
            distance = self.gain[numClusters][val]
            self.gain[numClusters]["avg"] += (distance / len(distMetrics))
            check = [1 if distance > avg else 0 for avg in avgList]
            if sum(check) > 2:
                return False

if __name__ == "__main__":
    featureDict = Util.read_features("../data/labdata/numberedVecs.tsv")
    keys = list(featureDict.keys())
    data = [featureDict[key]["vector"] for key in keys]
    clusterSolver = findNumClusters(data, len(data) / 100)
    print clusterSolver.kMeans()[0]
