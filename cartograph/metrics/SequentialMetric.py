import colour
from collections import defaultdict
import palettable.colorbrewer.sequential as sq

from cartograph.metrics.Utils import color_from_code


class SequentialMetric:
    # TODO: Document this
    def __init__(self, fields, colorCode, maxValue, mode='d', percentile=False, neutralColor='#777'):
        # Mode: Continuous or discrete
        # assert (len(colors) == 2)
        # assert (len(fields) == 1)
        self.fields = fields
        self.field = fields[0]
        self.palette = getattr(sq, colorCode)
        self.color = self.palette.colors
        self.numColors = self.palette.number
        self.neutralColor = colour.Color(neutralColor).rgb
        self.maxValue = maxValue
        self.percentile = percentile
        self.percentiles = {}
        self.mode = mode
        print self.color

    def train(self, points):
        if not self.percentile:
            return

        hist = defaultdict(int)
        for p in points:
            if self.field in p:
                hist[p[self.field]] += 1

        total = sum(hist.values())
        n = 0
        for k in sorted(hist.keys()):
            mid = n + hist[k] / 2
            self.percentiles[k] = 1.0 * mid / total
            n += hist[k]
        self.maxValue = 1.0
        print self.percentiles

    def getColor(self, point, zoom):

        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        if self.field not in point:
            return self.neutralColor + (alpha,)

        value = point[self.field]
        if self.percentile:
            value = int(self.percentiles[value] * self.numColors)
        else:
            value = point[self.field] * self.numColors/self.maxValue
        
        # Discrete mode
        if self.mode == 'd':
            return color_from_code(self.color[int(value)-1]) + (alpha,)
        
        # Continuous mode (pending)
        if self.mode == 'c':
            pass

    def adjustCountryColor(self, c, n):
        val = 0.97 ** (n + 1)
        return (val, val, val)


if __name__ == '__main__':
    sequentialData = [i for i in range(100)]
    points = []
    for i in sequentialData:
        point = {'foo': i}
        points.append(point)
    m = SequentialMetric(['foo'], sq.BuGn_7, 100, percentile=False)
    m.train(points)
    for i in sequentialData:
        print i, m.getColor({'foo': i, 'bar': 3, 'zpop': 1}, 1.0)

    m = SequentialMetric(['foo'], sq.BuGn_7, 100, percentile=True)
    m.train(points)
    for i in sequentialData:
        print i, m.getColor({'foo': i, 'bar': 3, 'zpop': 1}, 1.0)
