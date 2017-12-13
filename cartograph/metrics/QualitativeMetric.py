import colorsys

import colour
import palettable.colorbrewer.qualitative as q
import palettable.colorbrewer.sequential as sq
import palettable.colorbrewer.diverging as dv
import palettable.colorbrewer.qualitative as qu
from cartograph.metrics.Utils import color_from_code


class QualitativeMetric:
    def __init__(self, field, scale, colorscheme, neutralColor='#777'):
        """Initialize a QualitativeMetric. QualitativeMetric's main purpose is embodied by its .getColor() method, which
        provides the color information for a given point at a particular zoom level.

        FIXME: Because of the way data-files (i.e. TSVs) are currently loaded, it seems like this metric can't be used
        for a column containing purely numeric data.

        :param fields: string of name of the column to be used as a qualitative variable e.g. "name"
        :param scale: a list of strings, each of which is the name of a category
        :param colorCode: string of Python identifier of a color palette in module palettable.colorbrewer.qualitative
        :param neutralColor: str of form "#rgb" where r, g, & b are all hexadecimal digits 0-f for each color component
        """

        c = colorscheme
        if hasattr(sq, c):
            color_palette = getattr(sq, c)
        elif hasattr(dv, c):
            color_palette = getattr(dv, c)
        elif hasattr(qu, c):
            color_palette = getattr(qu, c)
        else:
            raise Exception("Unknown color palette: " + c)

        assert(color_palette.number == len(scale))  # FIXME: should be more informative error
        self.field = field
        self.scale = scale
        self.neutral_color = colour.Color(neutralColor).rgb
        self.color = color_palette.colors

    def getColor(self, point, zoom):
        """Get the color code for a point given a particular zoom level. The output is formatted in a list
        [r, g, b, a], where each element is a float between 0.0-1.0 representing the red, green, and blue components
        and the alpha (i.e. opacity) level.

        :param point: a point FIXME: what class is this supposed to be?
        :param zoom: the zoom level of the viewer as an integer. Higher zoom means the viewer is further zoomed out
        :return: an iterable whose components [r, g, b, a] represent red, green, blue, and alpha levels of point at zoom
        """
        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        # If the point doesn't have the column used for this metric, return neutral neutral
        if self.field not in point:
            return self.neutral_color + (alpha,)

        value = str(point[self.field])

        # If the value in the chosen column is out of the specified list, return neutral color
        if value not in self.scale:
            return self.neutral_color + (alpha,)
        
        scale_index = self.scale.index(value)
        return color_from_code(self.color[scale_index]) + (alpha,)

    def adjustCountryColor(self, c, contourNum, maxContour):
        assert(contourNum <= maxContour)
        (r, g, b, a) = c

        (h, l, s) = colorsys.rgb_to_hls(r, g, b)
        # Throw out lightness and recalculate it based on contours
        maxLight = 0.9
        minLight = 0.4
        l2 = maxLight - 1.0 * contourNum / maxContour * (maxLight - minLight)
        return colorsys.hls_to_rgb(h, l2, s)



# Test case
def test_qualitative():
    scale = ['A', 'B', 'C', 'D', 'E']
    m = QualitativeMetric(['foo'], scale, 'Dark2_5')
    from random import randint
    for i in range(10):
        point = {'foo': scale[randint(0,4)], 'zpop': 3}
        # print point['foo'], m.getColor(point, 1.0)
        assert all([x and y for x,y in zip(m.getColor(point, 1.0), m.color[scale.index(point[m.field])])])