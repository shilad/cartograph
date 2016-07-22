import numpy as np
import math
import copy
import matplotlib.colors as mc


class ColorSelector:

    def __init__(self, borders, colors):
        self.colors = colors
        self.countryBorders = list(borders[str(x)]['border_list'] for x in range(len(borders.keys())))
        self.colorDiff = self._sortColorsByDistances()
        self.centralities = self._countryCentralities()
        self.countryDiff = self._countryDistances()
        self.colorMatch = self._colorToDistance()

    def _sortColorsByDistances(self):
        colorDiff = {}
        used = []
        for i, key in enumerate(self.colors):
            used.append(i)
            color1 = key[3]
            for j, comp in enumerate(self.colors):
                if comp is not key and j not in used:
                    color2 = comp[3]
                    rgb1 = mc.hex2color(color1)
                    rgb2 = mc.hex2color(color2)
                    finalDif = 0
                    for i in range(3):
                        dif = math.fabs(rgb1[i] - rgb2[i])
                        finalDif += dif
                    colorDiff.setdefault(finalDif, []).append([i, j])

        return colorDiff

    def _countryCentralities(self):
        centralities = []
        for country in self.countryBorders:
            group = []
            regions = country[2:-2].split("], [")
            for region in regions:
                pts = region[1:-1].split("), (")
                for point in pts:
                    coords = point.split(", ")
                    finalCoord = [float(x) for x in coords]
                    group.append(finalCoord)
            centroid = np.mean(group, axis=0)
            centralities.append(centroid)

        return centralities

    def _countryDistances(self):
        dist = {}
        centers = self.centralities
        for i in range(len(centers)):
            dist[i] = {}
        for i, cent in enumerate(centers):
            for j, comp in enumerate(centers):
                if i is not j:
                    a = math.fabs(cent[0] - comp[0])
                    b = math.fabs(cent[1] - comp[1])
                    diff = math.sqrt(math.pow(a, 2) + math.pow(b, 2))
                    dist[i][diff] = j

        return dist

    def _getKeys(self, dictionary):
        keys = dictionary.keys()
        keys = sorted(keys)
        keys.reverse()
        return keys

    def _colorToDistance(self):
        colorMatch = {}
        cKeys = self.colorDiff.keys()
        cKeys = sorted(cKeys)
        colorFilled = []
        countryFilled = []
        for c in cKeys:
            for box in self.colorDiff[c]:
                if box[0] in colorFilled and box[1] not in colorFilled:
                    country = colorMatch[box[0]]
                    keys = self._getKeys(self.countryDiff[country])
                    for d in keys:
                        newCountry = self.countryDiff[country][d]
                        if newCountry not in countryFilled:
                            colorMatch[box[1]] = newCountry
                            colorFilled.append(box[1])
                            countryFilled.append(newCountry)
                            break

                elif box[1] in colorFilled and box[0] not in colorFilled:
                    country = colorMatch[box[1]]
                    keys = self._getKeys(self.countryDiff[country])
                    for d in keys:
                        newCountry = self.countryDiff[country][d]
                        if newCountry not in countryFilled:
                            colorMatch[box[0]] = newCountry
                            colorFilled.append(box[0])
                            countryFilled.append(newCountry)
                            break
                elif box[0] not in colorFilled and box[1] not in colorFilled:
                    stop = False
                    for i in range(len(self.countryDiff) - 1):
                        for country in range(len(self.countryDiff)):
                            if country not in countryFilled:
                                keys = self._getKeys(self.countryDiff[country])
                                newCountry = self.countryDiff[country][keys[i]]
                                if newCountry not in countryFilled:
                                    colorMatch[box[0]] = newCountry
                                    colorMatch[box[1]] = country
                                    colorFilled.append(box[0])
                                    colorFilled.append(box[1])
                                    countryFilled.append(country)
                                    countryFilled.append(newCountry)
                                    stop = True
                                    break
                        if stop:
                            break
        colorNotFilled = [x for x in range(len(self.colors)) if x not in colorFilled]
        countryNotFilled = [x for x in range(len(self.colors)) if x not in countryFilled]
        if colorNotFilled is not 0:
            for i in range(len(colorNotFilled)):
                colorMatch[colorNotFilled[i]] = countryNotFilled[i]


        return colorMatch


    def optimalColoring(self):
        color = {}
        keys = self.colorMatch.keys()
        for key in keys:
            color[self.colorMatch[key]] = self.colors[key]

        return color
