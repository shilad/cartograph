import re
import falcon
import logging
import os
import sys
from falcon_multipart.middleware import MultipartMiddleware
from cartograph.server.ParentService import ParentService, METACONF_FLAG
from cartograph.server.AddMapService import AddMapService
from cartograph.server.MapService import MapService
from cartograph.server.StaticService import StaticService
from cartograph.server.UploadService import UploadService

BASE_UPLOAD_DIR = 'data/upload'

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

if __name__ == '__main__' and len(sys.argv) > 1:
    meta_config_path = sys.argv[1]
else:
    meta_config_path = os.getenv('CARTOGRAPH_CONFIGS')
    if not meta_config_path:
        raise Exception, 'CARTOGRAPH_CONFIGS environment variable not set!'

# TODO: Can this line be deleted?
configs = {}

logging.info('configuring falcon')


# falcon.API instances are callable WSGI apps
app = falcon.API(middleware=[MultipartMiddleware()])


# Determine whether the input file is a multi-config (i.e. paths to multiple files) or a single config file
with open(meta_config_path, 'r') as meta_config:
    first_line = meta_config.readline().strip('\r\n').split(' ')
    if METACONF_FLAG not in first_line:
        map_services = {'_multi_map': False}
        conf_files = [meta_config_path]
    else:
        # Get a list of config_paths as separated by newlines and filter out the blank ones
        # (note that the .readline() above means we skip the first line)
        conf_files = filter(bool, re.split('[\\r\\n]+', meta_config.read()))

        assert len(first_line) == 2, "First line of meta-conf must be of format '###### server_name' where " \
                                     "'server_name' is a server namespace"
        map_services = {
            '_multi_map': True,
            '_server_alias': first_line[1],
            '_meta_config': meta_config_path,
            '_last_update': os.path.getmtime(meta_config_path)
        }

# Start up a set of services (i.e. a MapService) for each map (as specified by its config file)
for path in conf_files:
    map_service = MapService(path)
    map_services[map_service.name] = map_service


# Start a ParentService for each service; a ParentService represents a given service for every map in <map_services>
app.add_route('/{map_name}/search.json', ParentService(map_services, 'search_service'))
app.add_route('/{map_name}/vector/{layer}/{z}/{x}/{y}.topojson', ParentService(map_services, 'tile_service'))
app.add_route('/{map_name}/raster/{layer}/{z}/{x}/{y}.png', ParentService(map_services, 'mapnik_service'))
app.add_route('/{map_name}/template/{file}', ParentService(map_services, 'template_service'))
app.add_route('/{map_name}/point.json', ParentService(map_services, 'related_points_service'))
app.add_route('/{map_name}/log', ParentService(map_services, 'logging_service'))
app.add_route('/{map_name}/add_metric/{metric_type}', ParentService(map_services, 'add_metric_service'))
app.add_sink(ParentService(map_services, 'static_service').on_get, '/(?P<map_name>.+)/static')


# If the server is in multi-map mode, provide hooks for adding new maps
if map_services['_multi_map']:
    upload_dir = os.path.join(BASE_UPLOAD_DIR, map_services['_server_alias'])
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    app.add_route('/upload', UploadService(map_services, upload_dir))
    app.add_route('/add_map/{map_name}', AddMapService(map_services, upload_dir))


# Add way to get static files generally (i.e. without knowing the name of any active map)
app.add_sink(StaticService().on_get, '/static')


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
