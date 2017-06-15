import cPickle
import logging
import numpy as np
import os.path
from bisect import bisect_left

import annoy

from cartograph import Utils

logger = logging.getLogger("cartograph.fast-knn")

class FastKnn:
    def __init__(self, pathVectors, pathAnnoy=None, pathIds=None, format='text'):
        self.pathVectors = pathVectors
        if not pathAnnoy: pathAnnoy = pathVectors + ".annoy"
        if not pathIds: pathIds = pathVectors + ".annoyIds"
        self.pathAnnoy = pathAnnoy
        self.pathIds = pathIds
        self.index = None   # annoy index
        self.ids = None     # list of string ids, alphabetically sorted
        self.format = format

    def exists(self):
        for p in self.pathAnnoy, self.pathIds:
            if not os.path.isfile(p):
                return False
            if  os.path.getmtime(p) < os.path.getmtime(self.pathVectors):
                return False
        return True

    def readVectors(self):
        if self.format == 'text':
            vecs = Utils.read_vectors(self.pathVectors)
        elif self.format == 'mikolov':
            raise NotImplementedError()  # The code that follows will no longer work...
            vecs = {}
            for (id, vector) in readMikolov(self.pathVectors).items():
                vecs[id] = {'vector': vector}
        else:
            raise Exception, 'Unknown file format: ' + self.format

        if keyTransform:
            newVecs = {}
            for (k, v) in vecs.items():
                k2 = keyTransform(k)
                if k2:
                    newVecs[k2] = v
            vecs = newVecs
        assert(vecs)

        return vecs

    def rebuild(self):
        vecs = self.readVectors()

        ids = []
        n = None
        for k in range(len(vecs.index)):
            ids.append(vecs.iloc[k].name)
            if len(vecs.iloc[k][0]) == 0:
                pass
            elif n is None:
                n = len(vecs.iloc[k][0])
            else:
                assert(n == len(vecs.iloc[k][0]))
        ids.sort()

        ai = annoy.AnnoyIndex(n)
        for i in range(len(vecs.index)):
            if len(vecs.iloc[i][0]) == 0: continue
            j = binary_search(ids, vecs.iloc[i].name)
            ai.add_item(j, vecs.iloc[i][0])
            if i % 10000 == 0:
                logger.info('loading vector %d into annoy index' % i)
        logger.info('building annoy datastructure')
        ai.build(10)
        logger.info('saving annoy datastructure')
        ai.save(self.pathAnnoy)

        with open(self.pathIds, 'wb') as f:
            cPickle.dump([n] + ids, f)
        self.ids = ids
        self.index = ai

    def indexToId(self, index):
        return self.ids[index]

    def idToIndex(self, id):
        i = binary_search(self.ids, str(id))
        return (None if i < 0 else i)
        
    def read(self):
        with open(self.pathIds, 'rb') as f:
            data = cPickle.load(f)
            n = data[0]
            self.ids = data[1:]
        self.index = annoy.AnnoyIndex(n)
        self.index.load(self.pathAnnoy)

    def hasId(self, id):
        return self.idToIndex(id) is not None

    def getVector(self, id):
        index = self.idToIndex(id)
        if index is None:
            return None
        return self.index.get_item_vector(index)

    def neighbors(self, vec, n=5):
        r = self.index.get_nns_by_vector(vec, n, search_k=-1, include_distances=True)
        return list((self.ids[i], 1.0 - dist) for (i, dist) in zip(r[0], r[1]))

def binary_search(a, x, lo=0, hi=None):   # can't use a to specify default for hi
    hi = hi if hi is not None else len(a) # hi defaults to len(a)   
    pos = bisect_left(a,x,lo,hi)          # find insertion position
    return (pos if pos != hi and a[pos] == x else -1) # don't walk off the end



# ============================================= Test stuff ================================================

def nearestVector(knn, vectorID):
    if knn.exists():
        knn.read()
    else:
        knn.rebuild()

    selectedVector = np.array(knn.getVector(vectorID))  # Transform the vectorID into an array containing the selected vector's dimensions
    idDistanceDict = {}
    for id in knn.ids:
        if id != vectorID:  # prevents the function from just saying every vector is closest to itself. It is, but that's not helpful
            otherVector = np.array(knn.getVector(id))
            distance = scipy.spatial.distance.cosine(selectedVector, otherVector)
            idDistanceDict[id] = distance
    return min(idDistanceDict, key=idDistanceDict.get)

def testNeighbors():
    # Note to my future self: This test is O(n^2), so don't run it on large lists of vectors! Give it shortened files
    # with like 100 or so vectors in them so it'll run faster.

    tester = FastKnn("//Users/Sen/Desktop/ZipFileForTsvAndConfigFiles/oneHundredVectors.tsv")  # load in vectors
    if tester.exists():
        tester.read()
    else:
        tester.rebuild()

    numVectorsCalculated = 0
    numRight = 0
    numWrong = 0
    for id in tester.ids:
        neighborList = []  # probably not the most efficient, but there will only be 5 for each vector, so...
        for tuple in tester.neighbors(tester.getVector(id)):
             neighborList.append(int(tuple[0]))
        nearest = nearestVector(tester, id)
        if int(nearest) in neighborList:
            numRight += 1
        else:
            numWrong += 1
        numVectorsCalculated += 1

    percentRight = (numRight/numVectorsCalculated)*100
    percentWrong = (numWrong/numVectorsCalculated)*100
    print "%d chosen vectors compared to neighbor list. %d percent (%d) were on the list; %d percent (%d) were not." %\
          (numVectorsCalculated, percentRight, numRight, percentWrong, numWrong)
    assert (percentWrong <= 10)

