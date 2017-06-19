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


def add_conf(conf_path, app):
    if not os.path.isfile(conf_path):
        raise Exception, 'Cartograph Config Path %s does not exist' % `conf_path`

    conf = Config.initConf(conf_path)
    name = conf.get('DEFAULT', 'dataset')

    if os.getenv('CLEAR_CACHE'):
        logging.info('clearing cache directory %s' % conf.get('DEFAULT', 'webCacheDir'))
        shutil.rmtree(conf.get('DEFAULT', 'webCacheDir'), ignore_errors=True)

    if os.getenv('BASE_URL'):
        conf.set('Server', 'base_url', os.getenv('BASE_URL'))

    logging.info('intitializing services for ' + name)

    loggingService = LoggingService(conf)
    pointService = PointService(conf)
    countryService = CountryService(conf)
    tileService = TileService(conf, pointService, countryService)
    mapnikService = RasterService(conf, pointService, countryService)
    templateService = TemplateService(conf)
    staticService = StaticService(conf)
    searchService = SearchService(pointService)

    # things will handle all requests to the '/things' URL path
    prefix = '/' + name
    app.add_route(prefix + '/search.json', searchService)
    app.add_route(prefix + '/vector/{layer}/{z}/{x}/{y}.topojson', tileService)
    app.add_route(prefix + '/raster/{layer}/{z}/{x}/{y}.png', mapnikService)
    app.add_route(prefix + '/template/{file}', templateService)
    app.add_route(prefix + '/log', loggingService)
    app.add_sink(lambda req, resp: staticService.on_get(req, resp), prefix + '/static')