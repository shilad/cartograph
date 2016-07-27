import cPickle
import logging
import os.path
from bisect import bisect_left

import annoy

from cartograph import Utils

logger = logging.getLogger("cartograph.fast-knn")

class FastKnn:
    def __init__(self, pathVectors):
        self.pathVectors = pathVectors
        self.pathAnnoy = self.pathVectors + ".annoy"
        self.pathIds = self.pathVectors + ".annoyIds"
        self.index = None   # annoy index
        self.ids = None     # list of string ids, alphabetically sorted

    def exists(self):
        for p in self.pathAnnoy, self.pathIds:
            if not os.path.isfile(p):
                return False
            if  os.path.getmtime(p) < os.path.getmtime(self.pathVectors):
                return False
        return True

    def rebuild(self):
        vecs = Utils.read_features(self.pathVectors)
        assert(vecs)

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
        return (None if i < 0 else self.ids[i])
        
    def read(self):
        with open(self.pathIds, 'rb') as f:
            data = cPickle.load(f)
            n = data[0]
            self.ids = data[1:]
        self.index = annoy.AnnoyIndex(n)
        self.index.load(self.pathAnnoy)

    def neighbors(self, vec, n=5):
        r = self.index.get_nns_by_vector(vec, n, search_k=-1, include_distances=True)
        return list((self.ids[i], 1.0 - dist) for (i, dist) in zip(r[0], r[1]))

def binary_search(a, x, lo=0, hi=None):   # can't use a to specify default for hi
    hi = hi if hi is not None else len(a) # hi defaults to len(a)   
    pos = bisect_left(a,x,lo,hi)          # find insertion position
    return (pos if pos != hi and a[pos] == x else -1) # don't walk off the end
