import colour

class BivariateScaleMetric:
    def __init__(self, field, colors, maxValue):
        assert(len(colors) == 2)
        self.fields = [ field ]
        self.field = field
        self.color1 = colour.Color(colors[0]).rgb
        self.color2 = colour.Color(colors[1]).rgb
        self.maxValue = maxValue

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

        c1 = self.color1
        c2 = self.color2

        # Interpolate between the two colors.
        ns1 = 1.0 * n1 / (n1 + n2)
        ns2 = 1.0 * n2 / (n1 + n2)

        return (
            ns1 * c1[0] + ns2 * c2[0],
            ns1 * c1[1] + ns2 * c2[1],
            ns1 * c1[2] + ns2 * c2[2],
            alpha
        )


if __name__ == '__main__':
    m = BivariateScaleMetric('foo', ['blue', 'red'])
    print m.getColor({ 'foo' : 6, 'bar': 3, 'zpop' : 3.0 }, 1.0)
