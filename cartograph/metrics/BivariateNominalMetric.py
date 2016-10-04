import colour

class BivariateNominalMetric:
    def __init__(self, fields, scale, colors, sqrt=False, neutralColor='#777'):
        assert(len(colors) == 2)
        assert(len(fields) == 1)
        self.fields = fields
        self.field = fields[0]
        self.scale = scale
        self.sqrt = sqrt
        self.color1 = colour.Color(colors[0]).rgb
        self.color2 = colour.Color(colors[1]).rgb
        self.neutralColor = colour.Color(neutralColor).rgb

    def getColor(self, point, zoom):

        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        if self.field not in point :
            return self.neutralColor + (alpha,)

        value = point[self.field]
        if value not in self.scale:
            return self.neutralColor + (alpha,)

        # Interpolate between the two colors.
        i = self.scale.index(value)
        n = len(self.scale)

        if self.sqrt:
            i = i ** 0.5
            n = n ** 0.5

        ns1 = min(1.0, max(0, 1.0 * (n - i) / n))
        ns2 = 1.0 - ns1

        c1 = self.color1
        c2 = self.color2
        return (
            ns1 * c1[0] + ns2 * c2[0],
            ns1 * c1[1] + ns2 * c2[1],
            ns1 * c1[2] + ns2 * c2[2],
            alpha
        )


if __name__ == '__main__':
    m = BivariateScaleMetric('foo', ['blue', 'red'], 5)
    print m.getColor({ 'foo' : 1, 'bar': 3, 'zpop' : 3.0 }, 1.0)
