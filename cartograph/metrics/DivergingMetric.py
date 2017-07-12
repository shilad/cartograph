import colour
import palettable.colorbrewer.diverging as dv


class DivergingMetric:
    def __init__(self, fields, colorCode, minVal, maxVal, neutralColor='#888'):
        assert (len(fields) == 1)
        self.fields = fields
        self.field = fields[0]
        self.color = colorCode.colors
        self.numColors = colorCode.number
        self.neutralColor = colour.Color(neutralColor).rgb
        self.maxVal = maxVal
        self.minVal = minVal
        print self.color

    def getColor(self, point, zoom):
        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        if self.field not in point:
            return self.neutralColor + (alpha,)

        # Map point to a color in the palette based on percentile
        i = (point[self.field] - self.minVal) * self.numColors / (self.maxVal - self.minVal)

        return tuple(self.color[i]) + (alpha,)

    def adjustCountryColor(self, c, n):
        val = 0.97 ** (n + 1)
        return (val, val, val)


if __name__ == '__main__':
    m = DivergingMetric(['foo'], dv.PRGn_7, -10, 10)
    pos = [i for i in range(-10, 10)]
    points = []
    for i in pos:
        point = {'foo': i, 'bar': -i - 100, 'zpop': 1.0}
        points.append(point)
        print i, m.getColor(point, 1.0)
        correctColor = m.color[(point[m.field] - m.minVal) * m.numColors / (m.maxVal - m.minVal)]
        assert all([x & y for (x, y) in zip(m.getColor(point, 1.0)[:3], correctColor[:3])])
