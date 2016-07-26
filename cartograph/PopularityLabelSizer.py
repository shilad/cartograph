from collections import defaultdict

import numpy as np


class PopularityLabelSizer:
    def __init__(self, numBins, popularityList):
        self.numBins = numBins
        self.popularityList = popularityList
        self.assignedPopValues = list(range(self.numBins))

    def _calculateValueBreakpoints(self):
        popularityList = np.array(self.popularityList)
        unitStep = 100/self.numBins
        percentileDataValue = defaultdict(dict)
        percentileBreakpoints = list(range(0,100,unitStep))[1:]
        valueBreakpoints = []

        for i in range(len(percentileBreakpoints)-1):
            valueRange = np.percentile(popularityList, (percentileBreakpoints[i], percentileBreakpoints[i+1]))
            if i == 0:
                valueBreakpoints.append(valueRange[0])
            elif i == (len(percentileBreakpoints)-2):
                valueBreakpoints.append(valueRange[1])
            elif i > 0 and i < (len(percentileBreakpoints)-1):
                valueBreakpoints.extend(list(valueRange))

        valueBreakpoints.append(max(popularityList)+1)
        valueBreakpoints.insert(0, min(popularityList))

        return valueBreakpoints

    def calculatePopScore(self):
        valueBreakpoints = self._calculateValueBreakpoints()
        binIndex = []
        for item in self.popularityList:
            for i, breakpt in enumerate(valueBreakpoints):
                if item < breakpt:
                    binIndex.append(i-1)
                    break
        return binIndex



if __name__=='__main__':
    import Config
    from cartograph import Utils

    config = Config.BAD_GET_CONFIG()
    readPopularData = Utils.read_tsv(config.FILE_NAME_NUMBERED_POPULARITY)
    popularity = map(float, readPopularData['popularity'])
    popSizing = PopularityLabelSizer(5, popularity)

    print list(popSizing.calculatePopScore())
    # print(popSizing.calculateValueBreakpoints())
    # print(popSizing.labelPopularityScore())
