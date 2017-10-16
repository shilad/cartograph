# Main entry point for Cartograph map server
# Usage:  ./bin/docker-web.sh ./conf/my_maps.conf
# New map creation page is at http://localhost:4000/static/newMap.html


import re
import falcon
import logging
import os
import sys
from falcon_multipart.middleware import MultipartMiddleware

from cartograph.server import ServerConfig
from cartograph.server.MapDispatcher import MapDispatcher
from cartograph.server.ParentService import ParentService, METACONF_FLAG
from cartograph.server.AddMapService2 import AddMapService
from cartograph.server.Map import Map
from cartograph.server.StaticService import StaticService
from cartograph.server.UploadService import UploadService


logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Initialize the server configuration
if __name__ == '__main__' and len(sys.argv) > 1:
    server_config_path = sys.argv[1]
elif os.getenv('CARTOGRAPH_SERVER_CONFIG'):
    server_config_path = os.getenv('CARTOGRAPH_SERVER_CONFIG')
else:
    server_config_path = './conf/default_server.conf'
logging.info('using server config: ' + repr(server_config_path))
server_config = ServerConfig.init(server_config_path)

# Initialize the meta map configuration
# TODO: SWS: Make meta the only available config
if __name__ == '__main__' and len(sys.argv) > 2:
    meta_config_path = sys.argv[2]
elif os.getenv('CARTOGRAPH_CONFIGS'):
    meta_config_path = os.getenv('CARTOGRAPH_CONFIGS')
else:
    meta_config_path = server_config.get('DEFAULT', 'default_multi_map_config')
logging.info('using meta map config: ' + repr(meta_config_path))
if not os.path.isfile(meta_config_path):
    logging.info('meta map config doesnt exist, so creating an empty one.')
    open(meta_config_path, 'a').close()
server_config = ServerConfig.init(server_config_path)

configs = {}

logging.info('configuring falcon')


# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[MultipartMiddleware()])

dispatcher = MapDispatcher(app, server_config, meta_config_path)

# Start a ParentService for each service; a ParentService represents a given service for every map in <map_services>
dispatcher.add_route('/{map_name}/search.json', 'search_service')
dispatcher.add_route('/{map_name}/vector/{layer}/{z}/{x}/{y}.topojson', 'tile_service')
dispatcher.add_route('/{map_name}/raster/{layer}/{z}/{x}/{y}.png', 'mapnik_service')
dispatcher.add_route('/{map_name}/template/{file}', 'template_service')
dispatcher.add_route('/{map_name}/point.json', 'related_points_service')
dispatcher.add_route('/{map_name}/log', 'logging_service')
dispatcher.add_route('/{map_name}/add_metric/{metric_type}', 'add_metric_service')
dispatcher.add_route('/{map_name}/info', 'info_service')
dispatcher.add_sink('/(?P<map_name>.+)/static', 'static_service')

app.add_route('/upload', UploadService(server_config, dispatcher))
app.add_route('/add_map', AddMapService(server_config))

# Add way to get static files generally (i.e. without knowing the name of any active map)
app.add_sink(StaticService().on_get, '/static')


# Useful for debugging problems in your API; works with pdb.set_trace(). You
# can also use Gunicorn to host your app. Gunicorn can be configured to
# auto-restart workers when it detects a code change, and it also works
# with pdb.
if __name__ == '__main__':
    logging.info('starting server')

    from wsgiref import simple_server
    httpd = simple_server.make_server(server_config.get('DEFAULT', 'host'),
                                      int(server_config.get('DEFAULT', 'port')),
                                      app)
    logging.info('server ready!')
    httpd.serve_forever()
