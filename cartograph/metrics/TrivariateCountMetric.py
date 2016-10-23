import colour

class TrivariateCountMetric:
    def __init__(self, fields, colors, sqrt=False, nullColor='#aaa'):
        assert(len(colors) == 3)
        assert(len(fields) == 2)
        self.fields = fields
        self.field1 = fields[0]
        self.field2 = fields[1]
        self.sqrt = sqrt
        self.color1 = colour.Color(colors[0]).rgb
        self.color2 = colour.Color(colors[1]).rgb
        self.color3 = colour.Color(colors[2]).rgb
        self.nullColor = colour.Color(nullColor).rgb

    def getColor(self, point, zoom):

        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        n1 = point.get(self.field1, 0.0)
        n2 = point.get(self.field2, 0.0)
        if n1 + n2 == 0:
            return self.nullColor + (alpha,)

        p = 1.0 * n1 / (n1 + n2)
        if p >= 0.5:    # more of n1
            c = interpolate(self.color2, self.color1, 2.0 * (p - 0.5))
        else:           # more of n2
            c = interpolate(self.color2, self.color3, 2.0 * (0.5 - p))

        # Now interpolate between null color and the mix.
        p2 = (n1 + n2) / (n1 + n2 + 1.0)

        c = interpolate(self.nullColor, c, p2) + (alpha, )

        return c

    def adjustCountryColor(self, c, n):
        val = 0.97 ** (n + 1)
        return (val, val, val)

def interpolate(rgb1, rgb2, p):
    return (
        rgb1[0] * (1.0 - p) + rgb2[0] * p,
        rgb1[1] * (1.0 - p) + rgb2[1] * p,
        rgb1[2] * (1.0 - p) + rgb2[2] * p
    )