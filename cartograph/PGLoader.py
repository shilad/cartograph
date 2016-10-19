import luigi
import Config
import LuigiUtils
import Coordinates
from BorderGeoJSONWriter import CreateContinents
from ZoomGeoJSONWriter import CreateLabelsFromZoom
from Contour import CreateContours
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, LoadGeoJsonTask


class PGLoaderCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(LuigiUtils.__file__))


class LoadContoursDensity(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
                                 config,
                                 'contoursdensity',
                                 config.get('MapData',
                                            'density_contours_geojson'))

    def requires(self):
        return CreateContours(), PGLoaderCode()


class LoadContoursCentroid(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
                                 config,
                                 'contourscentroid',
                                 config.get('MapData',
                                            'centroid_contours_geojson'))

    def requires(self):
        return CreateContours(), PGLoaderCode()


class LoadCoordinates(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
                                 config,
                                 'coordinates',
                                 config.get('MapData', 'title_by_zoom'))

    def requires(self):
        return (
            Coordinates.CreateFullCoordinates(),
            PGLoaderCode(),
            CreateLabelsFromZoom()
        )


class LoadCountries(LoadGeoJsonTask):
    def __init__(self):
        config = Config.get()
        LoadGeoJsonTask.__init__(self,
                                 config, 'countries',
                                 config.get('MapData', 'countries_geojson'))

    def requires(self):
        return CreateContinents(), PGLoaderCode()
