import colour
import palettable.colorbrewer.diverging as dv

from cartograph.metrics.Utils import color_from_code


class DivergingMetric:
    def __init__(self, field, colorscheme, minVal, maxVal, neutralColor='#888'):
        """Initialize a DivergingMetric. A DivergingMetric's main purpose is embodied by its .getColor() method, which
        provides the color information for a given point at a particular zoom level. A DivergingMetric colors each point
        by the quantitative value in one of its columns.

        :param fields: string of name of the column to be used as a qualitative variable e.g. "name"
        :param colorCode: string of Python identifier of a color palette in module palettable.colorbrewer.qualitative
        :param neutralColor: str of form "#rgb" where r, g, & b are all hexadecimal digits 0-f for each color component
        """
        self.field = field
        if not hasattr(dv, colorscheme):
            raise ValueError, "Unknown color palette for diverging metric: " + repr(colorscheme)
        color_palette = getattr(dv, colorscheme)
        self.colors = color_palette.colors
        self.numColors = color_palette.number
        self.neutralColor = colour.Color(neutralColor).rgb
        self.maxVal = maxVal
        self.minVal = minVal

    def getColor(self, point, zoom):
        """Get the color code for a point given a particular zoom level. The output is formatted in a list
        [r, g, b, a], where each element is a float between 0.0-1.0 representing the red, green, and blue components
        and the alpha (i.e. opacity) level. The rgb components are determined by a combination of the color palette for
        this instance of DivergingMetric (i.e. self.colors).

        The specific color for a column value is determined by which of palette.number even subrange it falls in,
        between self.minVal and self.maxVal. E.g. if a palette has 4 colors (palette.number = 5), self.minVal = 0.0,
        self.maxVal = 5.0, points where 0 <= point[self.field] < 1.25 will return the 1st (0th) color in the palette,
        points where 1.25 <= point[self.field] < 2.5 will return the 2nd (1st) color in the palette, etc.

        :param point: a point FIXME: what class should this be? requires: self.minVal <= point[field] <= self.maxVal
        :param zoom: the zoom level of the viewer as an int. Higher zoom means the viewer is further zoomed out
        :return: a tuple whose components (r, g, b, a) represent red, green, blue, and alpha of point at zoom level
        """
        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        if self.field not in point:
            return self.neutralColor + (alpha,)

        # Map point to a color in the palette
        if point[self.field] >= self.maxVal:
            palette_index = self.numColors-1
        if point[self.field] <= self.minVal:
            palette_index = 0
        else:
            # Otherwise, assign colors based on which subrange the points value is in
            palette_index = (float(point[self.field]) - self.minVal) * self.numColors / (self.maxVal - self.minVal)

        return color_from_code(self.colors[int(palette_index)]) + (alpha,)

    def adjustCountryColor(self, c, n):
        val = 0.97 ** (n + 1)
        return (val, val, val)


def test_diverging():
    m = DivergingMetric(['foo'], 'PRGn_7', -10, 10)
    pos = [i for i in range(-10, 10)]
    points = []
    for i in pos:
        point = {'foo': i, 'bar': -i - 100, 'zpop': 1.0}
        points.append(point)
        # print i, m.getColor(point, 1.0)
        correctColor = m.colors[(point[m.field] - m.minVal) * m.numColors / (m.maxVal - m.minVal)]
        assert all([x and y for (x, y) in zip(m.getColor(point, 1.0)[:3], correctColor[:3])])
