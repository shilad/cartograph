# Let's get this party started!
import falcon
import logging
import sys

from cartograph import Config
from cartograph.server.CountryService import CountryService
from cartograph.server.MapnikService import MapnikService
from cartograph.server.PointService import PointService
from cartograph.server.SearchService import SearchService
from cartograph.server.TileService import TileService

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

conf = Config.initConf(sys.argv[1])

pointService = PointService(conf)
searchService = SearchService(pointService)
countryService = CountryService(conf)
tileService = TileService(conf, pointService, countryService)
mapnikService = MapnikService(conf)


# falcon.API instances are callable WSGI apps
app = falcon.API()

# things will handle all requests to the '/things' URL path
app.add_route('/search/{title}.json', searchService)
app.add_route('/vector/{layer}/{z}/{x}/{y}.topojson', tileService)
app.add_route('/raster/{layer}/{z}/{x}/{y}.png', mapnikService)

# Useful for debugging problems in your API; works with pdb.set_trace(). You
# can also use Gunicorn to host your app. Gunicorn can be configured to
# auto-restart workers when it detects a code change, and it also works
# with pdb.
if __name__ == '__main__':
    from wsgiref import simple_server
    httpd = simple_server.make_server('127.0.0.1', 4000, app)
    httpd.serve_forever()
