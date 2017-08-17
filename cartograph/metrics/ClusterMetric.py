import colorsys

import colour

from cartograph import MapConfig


class ClusterMetric:
    # TODO: Document this
    def __init__(self, conf):
        self.fields = []

        nc = conf.getint('PreprocessingConstants', 'num_contours')
        self.colors = {}
        self.colorCountries = True
        for cid, ccolors in MapConfig.getFullColorWheel().items():
            self.colors[cid] = colour.Color(ccolors[nc - 1]).rgb

        self.neutralColor = colour.Color("#777").rgb

    def getColor(self, point, zoom):
        # final alpha is related to the zoom
        depth = max(0.0, point['zpop'] - zoom)
        alpha = 0.7 ** depth

        c = point.get('clusterid')
        if c and c in self.colors:
            return self.colors[c] + (alpha,)
        else:
            return self.neutralColor + (alpha,)

    def adjustCountryColor(self, c, n):
        (r, g, b) = colour.Color(c).rgb
        (h, s, v) = colorsys.rgb_to_hsv(r, g, b)
        return colorsys.hsv_to_rgb(h, s * 0.5, (v + 1.0) / 2)
