import falcon
import logging
import os
import sys
import csv

from cartograph.server.ParentService import ParentService
from cartograph.server.NewMapService import AddMapService
from cartograph.server.MapService import MapService

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

if __name__ == '__main__' and len(sys.argv) > 1:
    meta_config = sys.argv[1]
else:
    meta_config = os.getenv('CARTOGRAPH_CONFIGS')
    if not meta_config:
        raise Exception, 'CARTOGRAPH_CONFIGS environment variable not set!'

configs = {}

logging.info('configuring falcon')

from falcon_multipart.middleware import MultipartMiddleware

# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[MultipartMiddleware()])


# Start up a set of services (i.e. a MapService) for each map (as specified by its config file)
map_services = {}
with open(meta_config, 'r') as conf_files:
    for path in conf_files:
        map_service = MapService(path.strip('\r\n'))
        map_services[map_service.name] = map_service
map_services['_meta_config'] = meta_config
map_services['_last_update'] = os.stat(meta_config)


# Start a ParentService for each service; a ParentService represents a given service for every map in <map_services>
app.add_route('/{map_name}/search.json',                         ParentService(map_services, 'search_service'))
app.add_route('/{map_name}/vector/{layer}/{z}/{x}/{y}.topojson', ParentService(map_services, 'tile_service'))
app.add_route('/{map_name}/raster/{layer}/{z}/{x}/{y}.png',      ParentService(map_services, 'mapnik_service'))
app.add_route('/{map_name}/template/{file}',                     ParentService(map_services, 'template_service'))
app.add_route('/{map_name}/log',                                 ParentService(map_services, 'logging_service'))
app.add_sink(ParentService(map_services, 'static_service').on_get, '/(?P<map_name>.+)/static')


# Add a hook for adding new maps, passing it a reference to the map_services dict, so it can add new maps to it
add_map_service = AddMapService(map_services)
app.add_route('/add_map.html', add_map_service)


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
