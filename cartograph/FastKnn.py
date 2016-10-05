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

    def readVectors(self, keyTransform):
        if self.format == 'text':
            vecs = Utils.read_features(self.pathVectors)
        elif self.format == 'mikolov':
            vecs = {}
            for (id, vector) in readMikolov(self.pathVectors).items():
                vecs[id] = { 'vector' : vector }
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

    def rebuild(self, keyTransform=None):
        vecs = self.readVectors(keyTransform)

        ids = []
        n = None
        for k, v in vecs.items():
            ids.append(k)
            if len(v['vector']) == 0:
                pass
            elif n is None:
                n = len(v['vector'])
            else:
                assert(n == len(v['vector']))
        ids.sort()

        ai = annoy.AnnoyIndex(n)
        for i, (k, v) in enumerate(vecs.items()):
            if len(v['vector']) == 0: continue
            j = binary_search(ids, k)
            ai.add_item(j, v['vector'])
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

def readMikolov(path):
    vectors = {}
    with open(path, 'rb') as f:
        header = f.readline()
        vocab_size, vector_size = map(int, header.split())  # throws for invalid file format

        binary_len = np.dtype(np.float32).itemsize * vector_size
        for i in range(vocab_size):

            word = []
            while True:
                ch = f.read(1)
                if ch == b' ':
                    break
                if ch == b'':
                    raise EOFError("unexpected end of input; is count incorrect or file otherwise damaged?")
                if ch != b'\n':  # ignore newlines in front of words (some binary files have)
                    word.append(ch)
            word = b''.join(word).decode('utf-8')
            weights = np.fromstring(f.read(binary_len), dtype=np.float32)
            vectors[word] = weights

            if i % 100000 == 0:
                logger.info('parsing %s, line %d of %d (id=%s)', path, i, vocab_size, word)

    return vectors
