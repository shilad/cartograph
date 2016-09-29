import math


class NormalizedMultinomialMetric:
    def __init__(self, fields, numBins=3, ignoreNeutral=True):
        self.fields = fields
        self.numBins = numBins
        self.ignoreNeutral = ignoreNeutral

    def assignCategory(self, point):
        maxField = None
        maxValue = 0.0
        for f in self.fields:
            k = 'smoothed' + f
            if k in point:
                v = point.get(k)
                if v > maxValue:
                    maxValue = v
                    maxField = f

        if not maxField:
            return None

        base = 1.0 / len(self.fields)
        if maxValue < base:
            return None

        b = int(math.floor((maxValue - base) / (1.0 - base) * (self.numBins + 1)))
        b = min(self.numBins, b)

        if b == 0 and self.ignoreNeutral:
            return None
        else:
            return maxField + '_' + str(b)

    def getMinThreshold(self, i):
        base = 1.0 / len(self.fields)
        return base + (1.0 - base) * i / (self.numBins + 1.0)

if __name__ == '__main__':
    m = NormalizedMultinomialMetric(['foo', 'bar'], 2)
    print m.getMinThreshold(1)
    print m.getMinThreshold(2)
    print m.getMinThreshold(3)
    for i in range(11):
        p = i / 10.0
        print p, m.assignCategory({'smoothedfoo' : p, 'smoothedbar' : (1-p)})
