# Let's get this party started!
import logging
import os
import sys

import falcon

from cartograph.server.NewMapService import AddMapService
from cartograph.server.MapService import MapService

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


# Add a hook for adding new maps
add_map_service = AddMapService(app)
app.add_route('/add_map.html', add_map_service)


# Start up a set of services for each map (as specified by its config file)


map_services = {}
for path in confPaths.split(':'):
    map_service = MapService(path, app)
    map_services[map_service.name] = map_service

app.add_route('/{name}/search.json', MapService('search_service'))
app.add_route('/{name}/vector/{layer}/{z}/{x}/{y}.topojson', self.tile_service)
app.add_route('/{name}/raster/{layer}/{z}/{x}/{y}.png', self.mapnik_service)
app.add_route('/{name}/template/{file}', self.template_service)
app.add_route('/{name}/log', self.logging_service)
app.add_sink(lambda req, resp: self.static_service.on_get(req, resp), prefix + '/static')


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
