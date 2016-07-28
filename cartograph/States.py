import luigi
import Config
import Utils
from Denoiser import Denoise
from BorderGeoJSONWriter import CreateContinents
from Contour import CreateContours
from luigiUtils import MTimeMixin, TimestampedLocalTarget
from sklearn.cluster import KMeans


class StateCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))


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
        config = Config.get()
        return TimestampedLocalTarget(config.FILE_NAME_STATE_CLUSTERS)

    def run(self):
        config = Config.get()
        #create dictionary of article ids to a dictionary with cluster numbers and vectors representing them
        articleDict = Utils.read_features(config.FILE_NAME_NUMBERED_CLUSTERS, config.FILE_NAME_NUMBERED_VECS)

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
            Utils.append_tsv(config.FILE_NAME_STATE_CLUSTERS,
                             ("index", "stateCluster"), keys, stateLabels)
        #CODE THUS FAR CREATES ALL SUBCLUSTERS, NOW YOU JUST HAVE TO FIGURE OUT HOW TO INTEGRATE THEM

        #ALSO HOW TO DETERMINE THE BEST # OF CLUSTERS FOR EACH SUBCLUSTER??? IT SEEMS LIKE THEY SHOULD VARY (MAYBE BASED ON # OF POINTS?)


        #then make sure those get borders created for them??
        #then create and color those polygons in xml