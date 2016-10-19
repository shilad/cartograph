import Popularity
import luigi
import Utils
import Config
import numpy as np
from LuigiUtils import TimestampedLocalTarget, MTimeMixin


class PopularityLabelSizerCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(__file__))


class PercentilePopularityIdentifier(MTimeMixin, luigi.Task):
    '''
    Bins the popularity values by given percentiles then maps the values to
    the unique article ID.
    '''
    def requires(self):
        return (Popularity.PopularityIdentifier(),
                PopularityLabelSizerCode())

    def output(self):
        config = Config.get()
        return (TimestampedLocalTarget(config.get("GeneratedFiles", "percentile_popularity_with_id")))

    def run(self):
        config = Config.get()
        readPopularData = Utils.read_tsv(config.get("GeneratedFiles", "popularity_with_id"))
        popularity = list(map(float, readPopularData['popularity']))
        index = list(map(int, readPopularData['id']))

        popLabel = PopularityLabelSizer(config.getint("MapConstants",
                                                      "num_pop_bins"),
                                        popularity)
        popLabelScores = popLabel.calculatePopScore()

        Utils.write_tsv(config.get("GeneratedFiles",
                                   "percentile_popularity_with_id"),
                        ("id", "popBinScore"), index, popLabelScores)


class PopularityLabelSizer:
    def __init__(self, numBins, popularityList):
        self.numBins = numBins
        self.popularityList = popularityList
        self.assignedPopValues = list(range(self.numBins))

    def _calculateValueBreakpoints(self):
        '''
        Given a list of popularity values associated to an article,
        determines the percentile breakpoints for specified number of bins. 
        '''
        popularityList = np.array(self.popularityList)
        unitStep = 100 / self.numBins
        percentileBreakpoints = list(range(0, 100, unitStep))[1:]
        valueBreakpoints = []

        for i in range(len(percentileBreakpoints) - 1):
            valueRange = np.percentile(popularityList,
                                       (percentileBreakpoints[i],
                                        percentileBreakpoints[i + 1]))
            if i == 0:
                valueBreakpoints.append(valueRange[0])
            elif i == (len(percentileBreakpoints) - 2):
                valueBreakpoints.append(valueRange[1])
            elif i > 0 and i < (len(percentileBreakpoints) - 1):
                valueBreakpoints.extend(list(valueRange))

        valueBreakpoints.append(max(popularityList) + 1)
        valueBreakpoints.insert(0, min(popularityList))

        return valueBreakpoints

    def calculatePopScore(self):
        '''
        Assigns each article point to a bin index, where points in
        higher bins are more popular. 
        '''
        valueBreakpoints = self._calculateValueBreakpoints()
        binIndex = []
        for item in self.popularityList:
            for i, breakpt in enumerate(valueBreakpoints):
                if item < breakpt:
                    binIndex.append(i - 1)
                    break
        return binIndex
