import luigi
import Config
import LuigiUtils
import Coordinates
from BorderGeoJSONWriter import CreateContinents
from Contour import CreateContours
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, LoadGeoJsonTask
from cartograph.CalculateZPop import CoordinatesGeoJSONWriter


class LoadContoursDensity(LoadGeoJsonTask):

    def __init__(self, *args, **kwargs):
        self._geoJsonPath = Config.get().get('MapData', 'density_contours_geojson')
        super(LoadContoursDensity, self).__init__(*args, **kwargs)

    @property
    def table(self): return 'contoursdensity'

    @property
    def geoJsonPath(self): return self._geoJsonPath

    def requires(self):
        return (
            CreateContours(),
        )



class LoadContoursCentroid(LoadGeoJsonTask):

    def __init__(self, *args, **kwargs):
        self._geoJsonPath = Config.get().get('MapData', 'centroid_contours_geojson')
        super(LoadContoursCentroid, self).__init__(*args, **kwargs)

    @property
    def table(self): return 'contourscentroid'

    @property
    def geoJsonPath(self): return self._geoJsonPath

    def requires(self):
        return (
            CreateContours(),
        )

class LoadCoordinates(LoadGeoJsonTask):

    def __init__(self, *args, **kwargs):
        self._geoJsonPath = Config.get().get('MapData', 'coordinates')
        super(LoadCoordinates, self).__init__(*args, **kwargs)

    @property
    def table(self): return 'coordinates'

    @property
    def geoJsonPath(self): return self._geoJsonPath

    def requires(self):
        return (
            CoordinatesGeoJSONWriter(),
        )


class LoadCountries(LoadGeoJsonTask):

    def __init__(self, *args, **kwargs):
        self._geoJsonPath = Config.get().get('MapData', 'countries_geojson')
        super(LoadCountries, self).__init__(*args, **kwargs)

    @property
    def table(self): return 'countries'

    @property
    def geoJsonPath(self): return self._geoJsonPath

    def requires(self):
        return (
            CreateContinents(),
        )