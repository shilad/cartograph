# Let's get this party started!
import falcon
import logging
import os
import shutil
import sys

from cartograph import Config
from cartograph.FreeText import FreeText
from cartograph.server.ConfigService import ConfigService
from cartograph.server.CountryService import CountryService
from cartograph.server.LoggingService import LoggingService
from cartograph.server.RasterService import RasterService
from cartograph.server.PointService import PointService
from cartograph.server.RelatednessService import RelatednessService
from cartograph.server.SearchService import SearchService
from cartograph.server.StaticService import StaticService
from cartograph.server.TemplateService import TemplateService
from cartograph.server.TileService import TileService

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

if __name__ == '__main__' and len(sys.argv) > 1:
    confPaths = sys.argv[1]
else:
    confPaths = os.getenv('CARTOGRAPH_CONFIGS')
    if not confPaths:
        raise Exception, 'CARTOGRAPH_CONFIGS environment variable not set!'

configs = {}

logging.info('configuring falcon')

# falcon.API instances are callable WSGI apps
app = falcon.API()

for path in confPaths.split(':'):
    if not os.path.isfile(path):
        raise Exception, 'Cartograph Config Path %s does not exist' % `path`

    conf = Config.initConf(path)
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
    # freeText = FreeText(conf.get('ExternalFiles', 'w2v'))
    # freeText.read()
    searchService = SearchService(pointService)
    # relatedService = RelatednessService(freeText, pointService)

    # things will handle all requests to the '/things' URL path
    prefix = '/' + name
    app.add_route(prefix + '/search.json', searchService)
    # app.add_route('/related.json', relatedService)
    app.add_route(prefix + '/vector/{layer}/{z}/{x}/{y}.topojson', tileService)
    app.add_route(prefix + '/raster/{layer}/{z}/{x}/{y}.png', mapnikService)
    app.add_route(prefix + '/template/{file}', templateService)
    app.add_route(prefix + '/log', loggingService)
    app.add_sink(lambda req, resp: staticService.on_get(req, resp), prefix + '/static')

app.add_sink(lambda req, resp: staticService.on_get(req, resp), '/static')

# Useful for debugging problems in your API; works with pdb.set_trace(). You
# can also use Gunicorn to host your app. Gunicorn can be configured to
# auto-restart workers when it detects a code change, and it also works
# with pdb.
if __name__ == '__main__':
    logging.info('starting server')

    from wsgiref import simple_server
    httpd = simple_server.make_server('0.0.0.0', 4000, app)
    logging.info('server ready!')
    httpd.serve_forever()
