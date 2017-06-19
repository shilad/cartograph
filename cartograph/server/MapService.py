import logging
import os
import shutil

from cartograph import Config
from cartograph.server.CountryService import CountryService
from cartograph.server.LoggingService import LoggingService
from cartograph.server.PointService import PointService
from cartograph.server.RasterService import RasterService
from cartograph.server.SearchService import SearchService
from cartograph.server.StaticService import StaticService
from cartograph.server.TemplateService import TemplateService
from cartograph.server.TileService import TileService


class MapService:
    """A set of services for a particular map    
    """
    def __init__(self, conf_path, app):
        if not os.path.isfile(conf_path):
            raise Exception, 'Cartograph Config Path %s does not exist' % `conf_path`
    
        conf = Config.initConf(conf_path)
        name = conf.get('DEFAULT', 'dataset')
    
        if os.getenv('CLEAR_CACHE'):
            logging.info('clearing cache directory %s' % conf.get('DEFAULT', 'webCacheDir'))
            shutil.rmtree(conf.get('DEFAULT', 'webCacheDir'), ignore_errors=True)
    
        if os.getenv('BASE_URL'):
            conf.set('Server', 'base_url', os.getenv('BASE_URL'))
    
        logging.info('initializing services for ' + name)
    
        self.logging_service = LoggingService(conf)
        self.point_service = PointService(conf)
        self.country_service = CountryService(conf)
        self.tile_service = TileService(conf, self.point_service, self.country_service)
        self.mapnik_service = RasterService(conf, self.point_service, self.country_service)
        self.template_service = TemplateService(conf)
        self.static_service = StaticService(conf)
        self.search_service = SearchService(self.point_service)

        # things will handle all requests to the '/things' URL path
        prefix = '/' + name
        app.add_route(prefix + '/search.json', self.search_service)
        app.add_route(prefix + '/vector/{layer}/{z}/{x}/{y}.topojson', self.tile_service)
        app.add_route(prefix + '/raster/{layer}/{z}/{x}/{y}.png', self.mapnik_service)
        app.add_route(prefix + '/template/{file}', self.template_service)
        app.add_route(prefix + '/log', self.logging_service)
        app.add_sink(lambda req, resp: self.static_service.on_get(req, resp), prefix + '/static')