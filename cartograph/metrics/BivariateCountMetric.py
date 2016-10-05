import colour

class BivariateCountMetric:
    def __init__(self, fields, colors, grayScale=True, neutralColor='#777'):
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

        a = 0.4
        r = 1.0 - a
        def strength(n): return a * (1 - r ** n) / (1 - r)
        s1 = strength(n1)
        s2 = strength(n2)

        c1 = (
            s1 * self.color1[0] + (1.0 - s1) * self.neutralColor[0],
            s1 * self.color1[1] + (1.0 - s1) * self.neutralColor[1],
            s1 * self.color1[2] + (1.0 - s1) * self.neutralColor[2]
        )

        c2 = (
            s2 * self.color2[0] + (1.0 - s2) * self.neutralColor[0],
            s2 * self.color2[1] + (1.0 - s2) * self.neutralColor[1],
            s2 * self.color2[2] + (1.0 - s2) * self.neutralColor[2]
        )

        # Interpolate between the two colors.
        ns1 = 1.0 * n1 / (n1 + n2)
        ns2 = 1.0 * n2 / (n1 + n2)

        return (
            ns1 * c1[0] + ns2 * c2[0],
            ns1 * c1[1] + ns2 * c2[1],
            ns1 * c1[2] + ns2 * c2[2],
            alpha
        )

    def adjustCountryColor(self, c, n):
        val = 0.95 ** (n + 1)
        return (val, val, val)

if __name__ == '__main__':
    m = BivariateCountMetric(['foo', 'bar'], ['blue', 'red'])
    print m.getColor({ 'foo' : 6, 'bar': 3, 'zpop' : 3.0 }, 1.0)
