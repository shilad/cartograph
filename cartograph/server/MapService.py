import logging
import os
import shutil

from cartograph import Config
from cartograph.server.CountryService import CountryService
from cartograph.server.LoggingService import LoggingService
from cartograph.server.PointService import PointService
from cartograph.server.RasterService import RasterService
from cartograph.server.RelatedPointsService import RelatedPointsService
from cartograph.server.SearchService import SearchService
from cartograph.server.StaticService import StaticService
from cartograph.server.TemplateService import TemplateService
from cartograph.server.TileService import TileService
from cartograph.server.RoadGetterService import RoadGetterService

class MapService:
    """A set of services for a particular map    
    """
    def __init__(self, conf_path):
        if not os.path.isfile(conf_path):
            raise Exception, 'Cartograph Config Path %s does not exist' % `conf_path`
    
        conf = Config.initConf(conf_path)
        self.name = conf.get('DEFAULT', 'dataset')
    
        if os.getenv('CLEAR_CACHE'):
            logging.info('clearing cache directory %s' % conf.get('DEFAULT', 'webCacheDir'))
            shutil.rmtree(conf.get('DEFAULT', 'webCacheDir'), ignore_errors=True)
    
        if os.getenv('BASE_URL'):
            conf.set('Server', 'base_url', os.getenv('BASE_URL'))
    
        logging.info('initializing services for ' + self.name)
    
        self.logging_service = LoggingService(conf)
        self.point_service = PointService(conf)
        self.country_service = CountryService(conf)
        self.tile_service = TileService(conf, self.point_service, self.country_service)
        self.mapnik_service = RasterService(conf, self.point_service, self.country_service)
        self.template_service = TemplateService(conf)
        self.related_points_service = RelatedPointsService(conf, self.point_service)
        self.static_service = StaticService(conf)
        self.search_service = SearchService(self.point_service)
        self.roads_service = RoadGetterService(
                                               "/Users/sen/PycharmProjects/CartoGraphRoadAPI/DataFiles/OriginalEdges.txt",
                                               "/Users/sen/PycharmProjects/CartoGraphRoadAPI/DataFiles/OriginalVertices.txt",
                                               "/Users/sen/PycharmProjects/CartoGraphRoadAPI/DataFiles/zpop.tsv")