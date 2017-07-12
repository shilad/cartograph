import colour
import matplotlib
import palettable.colorbrewer.qualitative as q

class QualitativeMetric:
    def __init__(self, fields, scale, colorCode, sqrt=False, neutralColor='#777'):
        assert(len(fields) == 1)
        assert(colorCode.number == len(scale))
        self.fields = fields
        self.field = fields[0]
        self.scale = scale
        self.sqrt = sqrt
        self.neutralColor = colour.Color(neutralColor).rgb
        self.color = colorCode.colors
        print self.color

    def getColor(self, point, zoom):

        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        if self.field not in point:
            return self.neutralColor + (alpha,)

        value = point[self.field]
        if value not in self.scale:
            return self.neutralColor + (alpha,)
        
        i = self.scale.index(value)
        return tuple(self.color[i]) + (alpha,)

    def adjustCountryColor(self, c, n):
        val = 0.97 ** (n + 1)
        return (val, val, val)


if __name__ == '__main__':
    scale = ['A', 'B', 'C', 'D', 'E']
    m = QualitativeMetric(['foo'], scale, q.Dark2_5)
    from random import randint
    points = []
    for i in range(10):
        point = {'foo': scale[randint(0,4)], 'zpop': 3}
        print point['foo'], m.getColor(point, 1.0)
        assert all([x&y for x,y in zip(m.getColor(point, 1.0), m.color[scale.index(point[m.field])])])