
import numpy as np
from sklearn.neighbors import KDTree
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from cartograph import Config
from cartograph.Config import initConf
from cartograph import Utils
from pprint import pprint

'''
Data source: labdata/macademia_comparative
About: Compare different embeddings of macademia data by calling peopleTable() and interestTable()
Returns: percentage of "overlap" by 2 different embeddings
Future: better/other measurements of nearest neighbors; change tsne parameters?
----
people comparation:
EI: 2D people only
IE: 2D people interpolated from interests
EE: 2D interests + people
----
interest comparation:
IE: 2D interests only
EI: 2D interests interpolated from ppl
EE: 2D interests + people
----
'''

def peopleTable():
	comparePeople(2)
	comparePeople(6)
	comparePeople(11)
	comparePeople(21)

def interestTable():
	compareInterest(2)
	compareInterest(6)
	compareInterest(11)
	compareInterest(21)

path_people = "../data/labdata/macademia_comparative/people/"
path_interest = "../data/labdata/macademia_comparative/interest/"


#===============================PEOPLE COMPARASION======================================
people_w2v_Dict = Utils.read_features(path_people + "people_names.tsv", 
									 path_people + "w2v_vecs.tsv")

people_EIDict = Utils.read_features(path_people + "people_names.tsv", 
								   path_people + "EI_coords.tsv")

people_IEDict = Utils.read_features(path_people + "IE_names.tsv", 
								   path_people + "IE_coords.tsv")

people_EEDict = Utils.read_features(path_people + "EE_names.tsv", 
								   path_people + "EE_coords.tsv")

people_pi_w2v_Dict = Utils.read_features(path_people + "EE_names.tsv", 
								   		path_people + "people_pi_w2v_vecs.tsv")

#===============================PEOPLE BUILD DICTIONARIES======================================

people_w2vKeys = list(people_w2v_Dict.keys())
people_w2vCoords = np.array([people_w2v_Dict[vID]["vector"] for vID in people_w2vKeys])
people_w2vNames = [people_w2v_Dict[nID]["name"] for nID in people_w2vKeys]

people_EIKeys = list(people_EIDict.keys())
people_EICoords = np.array([people_EIDict[vID]["coords"] for vID in people_EIKeys])
people_EINames = [people_EIDict[nID]["name"] for nID in people_EIKeys]

people_IEKeys = list(people_IEDict.keys())
people_IECoords = np.array([people_IEDict[vID]["coords"] for vID in people_IEKeys])
people_IENames = [people_IEDict[nID]["name"] for nID in people_IEKeys]

people_EEKeys = list(people_EEDict.keys())
people_EECoords = np.array([people_EEDict[vID]["coords"] for vID in people_EEKeys])
people_EENames = [people_EEDict[nID]["name"] for nID in people_EEKeys]

people_piKeys = list(people_pi_w2v_Dict.keys())
people_piCoords = np.array([people_pi_w2v_Dict[vID]["vector"] for vID in people_piKeys])
people_piNames = [people_pi_w2v_Dict[nID]["name"] for nID in people_piKeys]

#===============================INTEREST BUILD DICTIONARIES======================================
people_w2vTree = KDTree(people_w2vCoords, leaf_size=30)
people_IETree = KDTree(people_IECoords, leaf_size=30)
people_EITree = KDTree(people_EICoords, leaf_size=30)
people_EETree = KDTree(people_EECoords, leaf_size=30)
people_piTree = KDTree(people_piCoords, leaf_size=30)



#===============================INTEREST COMPARASION======================================

w2vDict = Utils.read_features(path_interest + "interest_names.tsv",
							 path_interest + "w2v_interest_vecs.tsv")

IEDict = Utils.read_features(path_interest + "interest_names.tsv",
							path_interest + "IE_interest_coords.tsv")

EIDict = Utils.read_features(path_interest + "EI_interest_names.tsv",
							path_interest + "EI_interest_coords.tsv")

EEDict = Utils.read_features(path_interest + "interest_names.tsv",
							path_interest + "EE_interest_coords.tsv")

#===============================INTEREST BUILD DICTIONARIES======================================

w2vKeys = list(w2vDict.keys())
w2vCoords = np.array([w2vDict[vID]["vector"] for vID in w2vKeys])
w2vNames = [w2vDict[nID]["name"] for nID in w2vKeys]

IEKeys = list(IEDict.keys())
IECoords = np.array([IEDict[vID]["coords"] for vID in IEKeys])
IENames = [IEDict[nID]["name"] for nID in IEKeys]

EIKeys = list(EIDict.keys())
EICoords = np.array([EIDict[vID]["coords"] for vID in EIKeys])
EINames = [EIDict[nID]["name"] for nID in EIKeys]

EEKeys = list(EEDict.keys())
EECoords = np.array([EEDict[vID]["coords"] for vID in EEKeys])
EENames = [EEDict[nID]["name"] for nID in EEKeys]

#===============================INTEREST BUILD DICTIONARIES======================================
w2vTree = KDTree(w2vCoords, leaf_size=30)
IETree = KDTree(IECoords, leaf_size=30)
EITree = KDTree(EICoords, leaf_size=30)
EETree = KDTree(EECoords, leaf_size=30)


def countNeighbors(tree1, tree2, vecs1, vecs2, names1, names2, numNeighbors):
	dict1 = {}
	dict2 = {}
	ct = 0
	for i in range(len(vecs1)):
	    Dist1, Ind1 = tree1.query([vecs1[i]], k = numNeighbors)
	    people_name_set = set()
	    Dist2, Ind2 = tree2.query([vecs2[i]], k = numNeighbors)
	    pi_name_set = set()


	    for j in Ind1[0]:
	    	people_name_set.add(names1[j])
	    dict1[names1[i]] = people_name_set
	    #people_name_set.remove(names1[i])

	    for k in Ind2[0]:
	    	pi_name_set.add(names2[k])
	    dict2[names2[i]] = pi_name_set
	    #pi_name_set.remove(names2[i])

	    ct += min(len(people_name_set), len(pi_name_set))

	count_dict = {}
	for name in names1:
		count_dict[name] = 0 #initialize
		for v in dict1[name]:
			if v in dict2[name]:
				count_dict[name] += 1

	#pprint(dict1)
	#pprint(dict2)

	print sum(count_dict.values())/float(ct)

	return count_dict


def compareInterest(n):
	'''
	n: number of neighbors considered
	Note: when n = 1, nearest neighbor usually is itself.
	'''
	print "===================INTEREST COMPARISION with", n-1, "neighbors===================="
	print "w2v vs. IE"
	countNeighbors(w2vTree, IETree, w2vCoords, IECoords, w2vNames, IENames, n)
	print "w2v vs. EE"
	countNeighbors(w2vTree, EETree, w2vCoords, EECoords, w2vNames, EENames, n)
	print "w2v vs. EI"
	countNeighbors(w2vTree, EITree, w2vCoords, EICoords, w2vNames, EINames, n)
	print '\n'
	print "IE vs. EE"
	countNeighbors(IETree, EETree, IECoords, EECoords, IENames, EENames, n)
	print "IE vs. EI"
	countNeighbors(IETree, EITree, IECoords, EICoords, IENames, EINames, n)
	print "EE vs. EI"
	countNeighbors(EETree, EITree, EECoords, EICoords, EENames, EINames, n)


def comparePeople(n):
	'''
	n: number of neighbors considered
	Note: when n = 1, nearest neighbor usually is itself.
	'''
	print "===================PEOPLE COMPARISION with", n-1, "neighbors===================="
	
	print "w2v vs. EI"
	countNeighbors(people_w2vTree, people_EITree, people_w2vCoords, people_EICoords, people_w2vNames, people_EINames, n)
	print "w2v vs. EE"
	countNeighbors(people_w2vTree, people_EETree, people_w2vCoords, people_EECoords, people_w2vNames, people_EENames, n)
	print "w2v vs. IE"
	countNeighbors(people_w2vTree, people_IETree, people_w2vCoords, people_IECoords, people_w2vNames, people_IENames, n)
	print '\n'
	print "EE vs. EI"
	countNeighbors(people_EETree, people_EITree, people_EECoords, people_EICoords, people_EENames, people_EINames, n)
	print "IE vs. EI"
	countNeighbors(people_IETree, people_EITree, people_IECoords, people_EICoords, people_IENames, people_EINames, n)
	print "IE vs. EE"
	countNeighbors(people_IETree, people_EETree, people_IECoords, people_EECoords, people_IENames, people_EENames, n)

	print "comparison in 200D"
	countNeighbors(people_w2vTree, people_piTree, people_w2vCoords, people_piCoords, people_w2vNames, people_piNames, n)



