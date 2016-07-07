import luigi
import os
import cartograph
import numpy as np
from sklearn.neighbors import KDTree
from sklearn.metrics.pairwise import cosine_similarity
from pprint import pprint

from cartograph import Config
from cartograph import Util
config = Config.BAD_GET_CONFIG()



peopleDict = Util.read_features(config.FILE_NAME_NUMBERED_VECS, #config people
								config.FILE_NAME_NUMBERED_NAMES,
								config.FILE_NAME_ARTICLE_COORDINATES)
peopleKeys = list(peopleDict.keys())
peopleVectors = np.array([peopleDict[vID]["vector"] for vID in peopleKeys])
peopleNames = [peopleDict[nID]["name"] for nID in peopleKeys]
x = [float(peopleDict[fID]["x"]) for fID in peopleKeys]
y = [float(peopleDict[fID]["y"]) for fID in peopleKeys]



interestDict = Util.read_features(config.FILE_NAME_MORE_VECS,
								config.FILE_NAME_MORE_NAMES)
interestKeys = list(interestDict.keys())
interestVectors = np.array([interestDict[vID]["vector"] for vID in interestKeys])
interestNames = [interestDict[nID]["name"] for nID in interestKeys]


kdt = KDTree(peopleVectors, leaf_size=30)


x_lst = []
y_lst = []
#knn_dict = {}
for i in range(len(interestVectors)):
	dist, ind = kdt.query([interestVectors[i]], k=5)
	temp_x_lst=[]
	temp_y_lst=[]
	temp_name_lst = []
	weights = []
	for j in ind[0]:
		temp_x_lst.append(x[j])
		temp_y_lst.append(y[j])
		temp_name_lst.append(peopleNames[j])
		weights.append(float(cosine_similarity([interestVectors[i]], [peopleVectors[j]]))) #cosine similarity >0
	#print weights
	#weights = [1,1,1,1,1]
	x_lst.append(np.average(temp_x_lst, axis = 0, weights = weights))
	y_lst.append(np.average(temp_y_lst, axis = 0, weights = weights))
	#knn_dict[interestNames[i]] = temp_name_lst


Util.write_tsv(config.FILE_NAME_MORE_COORDINATES,
              ("index", "x", "y"), interestKeys, x_lst, y_lst)


#pprint(knn_dict)

