import numpy as np
from collections import defaultdict
import bisect

class PopularityLabelSizer:
    def __init__(self, numBins, popularityList):
        self.numBins = numBins
        self.popularityList = np.array(popularityList)
        self.assignedPopValues = list(range(self.numBins))

    def calculateValueBreakpoints(self):
        percentileList = self.popularityList
        unitStep = 100/self.numBins
        percentileDataValue = defaultdict(dict)
        percentileBreakpoints = list(range(0,100,unitStep))[1:]
        valueBreakpoints = []

        for i in range(len(percentileBreakpoints)-1):
            valueRange = np.percentile(percentileList, (percentileBreakpoints[i], percentileBreakpoints[i+1]))
            if i == 0:
                valueBreakpoints.append(valueRange[0])
            elif i == (len(percentileBreakpoints)-2):
                valueBreakpoints.append(valueRange[1])
            elif i > 0 and i < (len(percentileBreakpoints)-1):
                valueBreakpoints.extend(list(valueRange))

        valueBreakpoints.append(max(percentileList))
        valueBreakpoints.insert(0, min(percentileList))
        return valueBreakpoints

    def calculatePopScore(self):
        valueBreakpoints = self.calculateValueBreakpoints()
        popScoreBins = np.empty(len(self.popularityList))
        for i in range(self.numBins):
            index = list(np.where((self.popularityList > valueBreakpoints[i]) & (self.popularityList < valueBreakpoints[i+1])))
            np.put(popScoreBins, index, i)
        return popScoreBins


    # def calculatePopScore(self, popValue):
    #     i = bisect.bisect(self.calculateValueBreakpoints(), popValue)
    #     return self.assignedPopValues[i]

    # def labelPopularityScore(self):
    #     return [self.calculatePopScore(popValue) for popValue in self.popularityList]


if __name__=='__main__':
    import Config
    import Util
    
    config = Config.BAD_GET_CONFIG()
    readPopularData = Util.read_tsv(config.FILE_NAME_NUMBERED_POPULARITY)
    popularity = map(float, readPopularData['popularity'])
    popSizing = PopularityLabelSizer(5, popularity)

    print(list(popSizing.calculatePopScore()))
    print(popSizing.calculateValueBreakpoints())
    # print(popSizing.labelPopularityScore())
