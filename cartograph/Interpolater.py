import cartograph
import numpy as np
from sklearn.neighbors import KDTree
from sklearn.metrics.pairwise import cosine_similarity
from pprint import pprint
from cartograph import Util

class Interpolater(object):
    """docstring for Interpolater"""
    def __init__(self, embeddedDict, interpolateDict, config):
        '''
        embeddedDict = Util.read_features(config.FILE_NAME_NUMBERED_VECS, 
                                        config.FILE_NAME_NUMBERED_NAMES,
                                        config.FILE_NAME_ARTICLE_COORDINATES)
        '''
        embeddedKeys = list(embeddedDict.keys())
        self.embeddedVectors = np.array([embeddedDict[vID]["vector"] for vID in embeddedKeys])
        self.embeddedNames = [embeddedDict[nID]["name"] for nID in embeddedKeys]
        self.x = [float(embeddedDict[fID]["x"]) for fID in embeddedKeys]
        self.y = [float(embeddedDict[fID]["y"]) for fID in embeddedKeys]
        '''
        interpolateDict = Util.read_features(config.FILE_NAME_MORE_VECS,
                                        config.FILE_NAME_MORE_NAMES)
        '''
        interpolateKeys = list(interpolateDict.keys())
        self.interpolateVectors = np.array([interpolateDict[vID]["vector"] for vID in interpolateKeys])
        self.interpolateNames = [interpolateDict[nID]["name"] for nID in interpolateKeys]
        self.interpolatePopularity = [interpolateDict[nID]["popularity"] for nID in interpolateKeys]
        self.config = config
        self.kdt = KDTree(self.embeddedVectors, leaf_size=30)


    def interpolatePoints(self):
        self.x_lst = []
        self.y_lst = []
        for i in range(len(self.interpolateVectors)):
            dist, ind = self.kdt.query([self.interpolateVectors[i]], k=5)
            temp_x_lst=[]
            temp_y_lst=[]
            temp_name_lst = []
            weights = []
            for j in ind[0]:
                temp_x_lst.append(self.x[j])
                temp_y_lst.append(self.y[j])
                temp_name_lst.append(self.embeddedNames[j])
                weights.append(float(cosine_similarity([self.interpolateVectors[i]], [self.embeddedVectors[j]]))) #cosine similarity >0
            #print weights
            #weights = [1,1,1,1,1]
            self.x_lst.append(np.average(temp_x_lst, axis = 0, weights = weights))
            self.y_lst.append(np.average(temp_y_lst, axis = 0, weights = weights))

        self._writeInterpolation()

    def _writeInterpolation(self):
        parentNames = self.config.get("ExternalFiles", "names_with_id")
        parentVecs = self.config.get("ExternalFiles", "vecs_with_id")
        parentCoords = self.config.get("PreprocessingFiles", "article_coordinates")
        parentPopularity = self.config.get("PreprocessingFiles", "popularity_with_id")

        newNames = self.config.get("InterpolateFiles", "new_names")
        newVecs = self.config.get("InterpolateFiles", "new_vecs")
        newCoords = self.config.get("InterpolateFiles", "new_coords")
        newPopularity = self.config.get("InterpolateFiles", "new_popularity")

        self.interpolateVectors = list(self.interpolateVectors)
        for i, vector in enumerate(self.interpolateVectors):
            string = ""
            for val in vector:
                string += str(val) + "\t"
            self.interpolateVectors[i] = string[:-1]
        Util.append_to_tsv(parentPopularity, newPopularity, self.interpolatePopularity)
        Util.append_to_tsv(parentVecs, newVecs, self.interpolateVectors)
        Util.append_to_tsv(parentNames, newNames, list(self.interpolateNames))
        Util.append_to_tsv(parentCoords, newCoords, list(self.x_lst), list(self.y_lst))



