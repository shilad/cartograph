import colour

class BivariateCountMetric:
    def __init__(self, fields, colors, grayScale=True, neutralColor='#888'):
        assert(len(fields) == 2)
        assert(len(colors) == 2)
        self.fields = fields
        self.field1 = fields[0]
        self.field2 = fields[1]
        self.grayScale = grayScale
        self.color1 = colour.Color(colors[0]).rgb
        self.color2 = colour.Color(colors[1]).rgb
        self.neutralColor = colour.Color(neutralColor).rgb

    def getColor(self, point, zoom):
        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth
        n1 = point.get(self.field1, 0.0)
        n2 = point.get(self.field2, 0.0)
        if n1 + n2 == 0:
            return self.neutralColor + (alpha,)

        p = (n1 + 1.5) / (n1 + n2 + 3.0)
        if p >= 0.5:
            c = self.color1
        else:
            c = self.color2

        s = abs(p - 0.5) * 2.0
        assert(0 <= s <= 1.0)
        return (
            s * c[0] + (1.0 - s) * self.neutralColor[0],
            s * c[1] + (1.0 - s) * self.neutralColor[1],
            s * c[2] + (1.0 - s) * self.neutralColor[2],
            alpha
        )

    def adjustCountryColor(self, c, n):
        val = 0.95 ** (n + 1)
        return (val, val, val)

if __name__ == '__main__':
    m = BivariateCountMetric(['foo', 'bar'], ['blue', 'red'])
    print m.getColor({ 'foo' : 6, 'bar': 3, 'zpop' : 3.0 }, 1.0)
