import colour

from cartograph import Config


class ClusterMetric:
    def __init__(self):
        self.fields = []

        conf = Config.get()
        nc = conf.getint('PreprocessingConstants', 'num_contours')
        self.colors = {}
        for cid, ccolors in Config.getColorWheel().items():
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
