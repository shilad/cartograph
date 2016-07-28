import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import distance
from sklearn.cluster import KMeans
import Utils

n = 5


class findNumClusters():
    def __init__(self, dataSet, maxClusters, minClusters=2):
        self.data = dataSet
        self.maxClusters = maxClusters
        self.minClusters = minClusters
        self.difference = []
        self.labels = []
        self.gain = {}

    def kMeans(self):
        for numClusters in range(self.minClusters, self.maxClusters + 1):
            self.gain[numClusters] = {}
            self.gain[numClusters]["avg"] = []
            for rep in range(n):
                clustId = numClusters
                print "Running on %s clusters, rep %s" % (numClusters, rep + 1)
                self.gain[clustId]["labels"] = list(KMeans(numClusters).fit(np.array(self.data)).labels_)
                centroids = [[0 for x in range(len(self.data[0]))]
                             for y in range(numClusters)]

                print "\tFinding Centroids"
                for index, pt in enumerate(self.data):
                    cluster = self.gain[clustId]["labels"][index]
                    prevCenter = centroids[cluster]
                    centroids[cluster] = self._solve_centroid(pt, prevCenter)

                self.gain[clustId]["cosine"] = 0
                self.gain[clustId]["cheby"] = 0
                self.gain[clustId]["euclid"] = 0
                self.gain[clustId]["jaccard"] = 0
                for index, pt in enumerate(self.data):
                    cluster = self.gain[clustId]["labels"][index]
                    centroid = centroids[cluster]
                    self.gain[clustId]["cosine"] += distance.cosine(centroid, pt) / len(self.data)
                    self.gain[clustId]["cheby"] += distance.chebyshev(centroid, pt) / len(self.data)
                    self.gain[clustId]["jaccard"] += distance.correlation(centroid, pt) / len(self.data)

                marginGain = self.bestMarginalGain(clustId, rep, centroids)
                if marginGain[0] is False:
                    return marginGain[1], self.gain[marginGain[0]]["labels"]

        print "Max clusters is best marginal gain," + \
              "consider rerunning with higher max"
        return self.maxClusters, self.gain[clustId]["labels"]

    def _solve_centroid(self, vec1, vec2):
        if len(vec1) != len(vec2):
            print "Not equal vectors"
            raise IndexError
        centroid = []
        for index, val in enumerate(vec1):
            avg = (val + vec2[index]) / 2
            centroid.append(avg)

        return centroid

    def bestMarginalGain(self, clustID, rep, labels):
        print "\tChecking Marginal Gain"

        self.gain[clustID]["avg"].append(0)

        keys = self.gain.keys()
        avgList = [self.gain[key]["avg"] for key in keys]
        distMetrics = ["cosine", "cheby", "jaccard"]
        distances = [self.gain[clustID][dist] for dist in distMetrics]
        print "\tDistances: %s" % (str(distances))
        for dist in distances:
            self.gain[clustID]["avg"][-1] += (dist / len(distMetrics))

        avgList = [self.gain[key]["avg"] for key in keys]
        dist = sum(self.gain[clustID]["avg"]) / len(self.gain[clustID]["avg"])

        x = list(keys)
        fig, ax = plt.subplots()
        ax.boxplot([self.gain[key]["avg"] for key in keys],
                   labels=x)
        plt.draw()
        plt.savefig("././data/FullEnglish/numClusters.png")
        plt.close(fig)
        print "\tSaved image to file"
        if len(avgList) > 1:
            prevAvg = sum(avgList[-2]) / len(avgList[-2])
            print "\tPrevious Avg: " + str(prevAvg)
        else:
            prevAvg = float("inf")
        print "\tCurrent Dist: " + str(dist)

        if n == rep - 1:
            for avg in avgList:
                repAvg = sum(avg) / len(avg)
                if prevAvg < repAvg:
                    print "\tBest avg: %s, With %s clusters" % (prevAvg, avgList[-2])
                    plt.show()
                    return False, avgList.index(avg)
                elif prevAvg * .9 < repAvg:
                    print "\tBest avg: %s, With %s clusters" % (repAvg, clustID)
                    return False, clustID
        return True, clustID

if __name__ == "__main__":
    featureDict = Util.read_features("././data/FullEnglish/labdata/numberedVecsFull.tsv")
    keys = list(featureDict.keys())
    data = [featureDict[key]["vector"] for key in keys]
    clusterSolver = findNumClusters(data, len(data) / 100)
    print clusterSolver.kMeans()[0]
