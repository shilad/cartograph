import luigi
import sys

sys.setrecursionlimit(10000) # 10000 is an example, try with different values

from cartograph import Colors
from cartograph.PGLoader import LoadContoursDensity, LoadContoursCentroid, LoadCoordinates, LoadCountries


class ParentTask(luigi.Task):

    def requires(self):
        return (
            LoadContoursDensity(),
            LoadContoursCentroid(),
            LoadCoordinates(),
            LoadCountries(),
            Colors.ColorsCode()
        )
