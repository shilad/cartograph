from pygsp import graphs, filters
import numpy as np

class Denoiser:

    def __init__(self, x, y, clusters):
        self.x = x
        self.y = y
         self.clusters = clusters





src = '/Users/research/Desktop/testing.csv'
pt25000 = '/Users/research/Desktop/data25000.txt'


#==========================Create Filters=============================

data = np.genfromtxt(src, delimiter = ",", usecols = (0, 1, 2), skip_header = 1)
size = data.size / 3

# def getData(path):

# 	data = np.genfromtxt(path, delimiter = ",", usecols = (0, 1), skip_header = 1) #all points
# 	return data


def filter():
	G = graphs.NNGraph(data[:,[0,1]]) #k = 10
	G.estimate_lmax()
	fn = filters.Heat(G) #tau = 10, higher tau, spikier signal, less points
	return fn

#==========================Do Analysis=============================


def filter_in(numClusters):
    m = filter()
    s = np.empty(size*numClusters).reshape(numClusters, size) #s: 10xn signals
    v = np.zeros(size*numClusters).reshape(numClusters, size) #v: 10xn matrix of initial vectors
	for i in range(numClusters):
		ct = -1
		for j in data[:,2]:
			ct += 1
			if j == i: v[i][ct] = 1 #check index
		s[i] = m.analysis(v[i])
	return np.transpose(s)


def filterOut(dataIn, numClusters):
	s = filterIn(numClusters)
	dataOut = np.zeros(3).reshape(1,3)
	for i in range(size):
		num = int(np.where(s == max(s[i]))[1][0])
		if num == dataIn[i][2]:
			dataOut = np.insert(dataOut, 0, dataIn[i], axis = 0)

	dataOut = np.delete(dataOut, -1, 0)
	np.savetxt('dataFinal.txt', dataOut, delimiter = ',')
	return dataOut


s = filterOut(data, 10)