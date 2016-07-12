import numpy as np


class ColorSelector:

    def __init__(self, borders, colors):
        self.colors = colors
        keys = list(borders.keys())
        self.countryBorders = [borders[x]['border_list'] for x in keys]
        # self.centralities = self._countryCentralities()

    def _sortColorsByDistances(self):
        pass

    def _countryCentralities(self):
        centralities = []
        for country in self.countryBorders:
            group = []
            for polygon in country:
                for pt in polygon:
                    group.append(pt)
            centroid = np.mean(group, axis=0)
            centralities.append(centroid)

        return centralities

    def _countryDistances():
        pass

    def optimalColoring(self):
        return self.colors
