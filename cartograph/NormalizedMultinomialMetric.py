import math
import colour


class NormalizedMultinomialMetric:
    def __init__(self, fields, colors, numBins=3, ignoreNeutral=True):
        self.fields = fields
        self.colors = [colour.Color(c) for c in colors]
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

    def getColors(self, zoom):
        byGroup = {}
        for (f, c) in zip(self.fields, self.colors):
            for i in range(1, self.numBins+1):
                key = f + '_' + str(i)
                byGroup[key] = {}
                baseOpacity = 0.8 * i / self.numBins
                for z in range(20):
                    opacity = baseOpacity * (0.6 ** max(0, z - zoom))
                    byGroup[key][z] = (c.red, c.green, c.blue, opacity)
        byGroup[None] = {}
        for z in range(20):
            opacity = 0.15 * (0.6 ** max(0, z - zoom))
            byGroup[None][z] = (0.0, 0.0, 0.0, opacity)
        return byGroup

    def getMinThreshold(self, i):
        base = 1.0 / len(self.fields)
        return base + (1.0 - base) * i / (self.numBins + 1.0)

if __name__ == '__main__':
    m = NormalizedMultinomialMetric(['foo', 'bar'], ['blue', 'green'], 2)
    print m.getMinThreshold(1)
    print m.getMinThreshold(2)
    print m.getMinThreshold(3)
    for i in range(11):
        p = i / 10.0
        print p, m.assignCategory({'smoothedfoo' : p, 'smoothedbar' : (1-p)})

    for (zoom, colors) in m.getColors(5).items():
        print zoom, colors
