from __future__ import unicode_literals

import json, os, shutil
import multiprocessing
import gunicorn.app.base
from gunicorn.six import iteritems

import TileStache
import cartograph
from ModestMaps.Core import Coordinate



def number_of_workers():
    return (multiprocessing.cpu_count() * 2) + 1


class StandaloneApplication(gunicorn.app.base.BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application



def run_server(path_cfg):
    path_cfg = os.path.abspath(path_cfg)
    path_cache = json.load(open(path_cfg, 'r'))['cache']['path']
    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    if os.path.isdir(path_cache):
        assert(len(path_cache) > 5)
        shutil.rmtree(path_cache)

    app = CartographServer(path_cfg)
    print('warming up tile cache...')
    app.warmup()
    print('done warming up tile cache...')
    options = {
        'bind': '%s:%s' % ('0.0.0.0', '8080'),
        'static
        'workers': number_of_workers(),
    }
    StandaloneApplication(app, options).run()


class CartographServer(TileStache.WSGITileServer):
    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic'):
            response = Response ('Hello, world' + path_info)
            return response(environ, start_response)
        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)

    def warmup(self):
        layer = TileStache.requestLayer(self.config, '/map/0/0/0.png').getTileResponse(Coordinate(0, 0, 0), 'png')


