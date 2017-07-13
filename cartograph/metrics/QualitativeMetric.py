import colour
import palettable.colorbrewer.qualitative as q
from cartograph.metrics.Utils import color_from_code


class QualitativeMetric:
    def __init__(self, fields, scale, colorCode, sqrt=False, neutralColor='#777'):
        assert(len(fields) == 1)  # FIXME: should be a more informative error
        color_palette = getattr(q, colorCode)
        assert(color_palette.number == len(scale))  # FIXME: should be more informative error
        self.fields = fields
        self.field = fields[0]
        self.scale = scale
        self.sqrt = sqrt
        self.neutral_color = colour.Color(neutralColor).rgb
        self.color = color_palette.colors

    def getColor(self, point, zoom):
        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        # If the point doesn't have the column used for this metric, return neutral neutral
        if self.field not in point:
            return self.neutral_color + (alpha,)

        value = point[self.field]

        # If the value in the chosen column is out of the specified list, return neutral color
        if value not in self.scale:
            return self.neutral_color + (alpha,)
        
        scale_index = self.scale.index(value)
        return color_from_code(self.color[scale_index]) + (alpha,)

    def adjustCountryColor(self, c, n):
        val = 0.97 ** (n + 1)
        return (val, val, val)


# Test case
if __name__ == '__main__':
    scale = ['A', 'B', 'C', 'D', 'E']
    m = QualitativeMetric(['foo'], scale, q.Dark2_5)
    from random import randint
    points = []
    for i in range(10):
        point = {'foo': scale[randint(0,4)], 'zpop': 3}
        print point['foo'], m.getColor(point, 1.0)
        assert all([x&y for x,y in zip(m.getColor(point, 1.0), m.color[scale.index(point[m.field])])])