# Let's get this party started!
import falcon
import logging
import os
import shutil
import sys

from cartograph import Config
from cartograph.server.ConfigService import ConfigService
from cartograph.server.CountryService import CountryService
from cartograph.server.MapnikService import MapnikService
from cartograph.server.PointService import PointService
from cartograph.server.SearchService import SearchService
from cartograph.server.StaticService import StaticService
from cartograph.server.TemplateService import TemplateService
from cartograph.server.TileService import TileService

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

if __name__ == '__main__' and len(sys.argv) > 1:
    confPath = sys.argv[1]
else:
    confPath = os.getenv('CARTOGRAPH_CONFIG')
    if not confPath:
        raise Exception, 'CARTOGRAPH_CONFIG environment variable not set!'

if not os.path.isfile(confPath):
    raise Exception, 'Cartograph Config Path %s does not exist' % `confPath`

conf = Config.initConf(confPath)

if os.getenv('CLEAR_CACHE'):
    logging.info('clearing cache directory %s' % conf.get('DEFAULT', 'webCacheDir'))
    shutil.rmtree(conf.get('DEFAULT', 'webCacheDir'), ignore_errors=True)

logging.info('intitializing services')

pointService = PointService(conf)
searchService = SearchService(pointService)
countryService = CountryService(conf)
tileService = TileService(conf, pointService, countryService)
mapnikService = MapnikService(conf, pointService, countryService)
configService = ConfigService(conf)
templateService = TemplateService(conf)
staticService = StaticService(conf)

logging.info('configuring falcon')

# falcon.API instances are callable WSGI apps
app = falcon.API()

# things will handle all requests to the '/things' URL path
app.add_route('/search.json', searchService)
app.add_route('/vector/{layer}/{z}/{x}/{y}.topojson', tileService)
app.add_route('/raster/{layer}/{z}/{x}/{y}.png', mapnikService)
app.add_route('/config.js', configService)
app.add_route('/template/{file}', templateService)
app.add_sink(lambda req, resp: staticService.on_get(req, resp), '/static')

# Useful for debugging problems in your API; works with pdb.set_trace(). You
# can also use Gunicorn to host your app. Gunicorn can be configured to
# auto-restart workers when it detects a code change, and it also works
# with pdb.
if __name__ == '__main__':
    logging.info('starting server')

    from wsgiref import simple_server
    httpd = simple_server.make_server('127.0.0.1', 4000, app)
    logging.info('server ready!')
    httpd.serve_forever()
