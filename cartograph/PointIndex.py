import heapq
import math

import numpy as np
from scipy.spatial import cKDTree, KDTree


class PointIndex:
    def __init__(self, ids, X, Y, pops):
        self.ids = list(ids)
        self.area = (max(X) - min(X)) * (max(Y) - min(Y))
        self.data = np.array(zip(X, Y))
        self.pops = list(pops)
        self.sortedIndexes = sorted(range(len(self.ids)), key=lambda i: pops[i], reverse=True)
        self.tree = KDTree(self.data)

    def queryRect(self, x0, y0, x1, y1, n=None):

        # Decide whether we use brute force or not.
        qArea =(x1 - x0) * (y1 - y0)
        frac = qArea / self.area
        numMatches = len(self.ids) * frac
        if n is None: n = numMatches

        # KD tree is SUPER fast, ignore it. Just worry about the heap
        expGeoOps = numMatches * math.log(n)
        expBFOps = len(self.ids)
        useBruteForce = expBFOps < 10 * expGeoOps
        # print frac, numMatches, expGeoOps, expBFOps, useBruteForce

        if useBruteForce:
            # print "BRUTE"
            top = []
            for i in self.sortedIndexes:
                x, y = self.data[i]
                if x < x0 or x > x1 or y < y0 or y > y1:
                    continue

                top.append((self.pops[i], self.ids[i], x, y))
                if len(top) >= n:
                    break
            return top
        else:
            # print "ACCEL"
            assert(x0 <= x1)
            assert(y0 <= y1)
            x = (x0 + x1) / 2.0
            y = (y0 + y1) / 2.0
            r = max(x - x0, y - y0) * 2

            # for i, id in enumerate(self.ids):
            #     if id == '12706':
            #         print i, id, self.data[i], self.pops[i]
            # #
            # print r, x, y
            results = self.tree.query_ball_point((x, y), r=r, p=1.0)

            top = []
            for i in results:
                x, y = self.data[i]
                if x < x0 or x > x1 or y < y0 or y > y1:
                    continue
                t = (self.pops[i], self.ids[i], x, y)
                if n is None or len(top) < n:
                    heapq.heappush(top, t)
                elif top[0][0] < t[0]:
                    heapq.heapreplace(top, t)

            return top


if __name__ == '__main__':
    import random
    import time
    last = time.time()
    def timeit(label):
        global last
        print '%s: %.4f seconds' % (label, time.time() - last)
        last = time.time()
    N = 5000000
    points = np.random.uniform(0, 1, (N, 2))
    ids = (np.arange(N) + 1) * 2
    pops = np.random.uniform(0, 100.0, N)
    timeit('point creation, n=%d' % N)
    pi = PointIndex(ids, points[:,0], points[:,1], pops)
    timeit('index creation')
    # for size in (0.001, 0.01, 0.1, 1.0):
    for size in (0.01, 0.1, 0.2, 0.3, .5, 1.0):
        lens = []
        pops  = []
        for i in range(1):
            x0 = random.random()
            y0 = random.random()
            results = pi.queryRect(x0, y0, x0 + size, y0 + size, 100)
            lens.append(len(results))
            pops.extend(r[0] for r in results)

        l = 1.0 * sum(lens) / len(lens)
        p = 1.0 * sum(pops) / len(pops)
        timeit('100 queries of size %f' % (size,))
        print('mean lens=%f, mean pops=%f' % (l, p))




