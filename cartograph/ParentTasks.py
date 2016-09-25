import luigi

from cartograph import Colors, MapStyler
from cartograph.Choropleth import AllChoropleth
from cartograph.PGLoader import LoadContoursDensity, LoadContoursCentroid, LoadCoordinates, LoadCountries


class ParentTask(luigi.WrapperTask):

    def requires(self):
        return (
            LoadContoursDensity(),
            LoadContoursCentroid(),
            LoadCoordinates(),
            LoadCountries(),
            Colors.ColorsCode(),
            AllChoropleth(),
            MapStyler.CreateMapXml()
        )