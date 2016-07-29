import numpy as np
from sklearn.neighbors import KDTree
from os import sys, path
sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from cartograph import Config
from cartograph.Config import initConf
from cartograph import Utils


def writeFile(inpath1, inpath2, outpath):
	#2D interpolated interests
	interpolateDict = Utils.read_features(inpath1, inpath2)
	print len(interpolateDict)

	Keys = []
	for i in range(1998):
		Keys.append(str(i+7378))

	Vectors = list(np.array([interpolateDict[vID]["vector"] for vID in Keys]))


	for i, vector in enumerate(Vectors):
				string = ""
				for val in vector:
					string += str(val) + "\t"
				Vectors[i] = string[:-1]

	Utils.write_tsv(outpath, ("index", "vector"), Keys, Vectors)