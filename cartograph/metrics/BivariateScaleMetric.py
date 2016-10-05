import colour

class BivariateScaleMetric:
    def __init__(self, fields, colors, maxValue, neutralColor='#777'):
        assert(len(colors) == 2)
        assert(len(fields) == 1)
        self.fields = fields
        self.field = fields[0]
        self.color1 = colour.Color(colors[0]).rgb
        self.color2 = colour.Color(colors[1]).rgb
        self.neutralColor = colour.Color(neutralColor).rgb
        self.maxValue = maxValue

    def getColor(self, point, zoom):

        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        if self.field not in point:
            return self.neutralColor + (alpha,)

        # Interpolate between the two colors.
        value = point[self.field]
        ns1 = min(1.0, max(0, 1.0 * (self.maxValue - value) / self.maxValue))
        ns2 = 1.0 - ns1

        c1 = self.color1
        c2 = self.color2
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
    m = BivariateScaleMetric('foo', ['blue', 'red'], 5)
    print m.getColor({ 'foo' : 1, 'bar': 3, 'zpop' : 3.0 }, 1.0)
