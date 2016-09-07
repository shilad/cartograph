import luigi

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