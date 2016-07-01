import json, os, shutil

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

import Util
import Config

import TileStache

config = Config.BAD_GET_CONFIG()

def run_server(path_cfg):
    path_cfg = os.path.abspath(path_cfg)
    path_cache = json.load(open(path_cfg, 'r'))['cache']['path']
    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    if os.path.isdir(path_cache):
        assert(len(path_cache) > 5)
        shutil.rmtree(path_cache)

    app = CartographServer(path_cfg)
    run_simple('0.0.0.0', 8080, app, static_files=static_files)


class CartographServer(TileStache.WSGITileServer):
    def __call__(self, environ, start_response):
        
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic'):

             #dictionary of article ids to points and titles
            xyDict = Util.read_features(config.FILE_NAME_ARTICLE_COORDINATES,
                                         config.FILE_NAME_NUMBERED_NAMES)
            
            response = Response ()
            
           
            return response(environ, start_response)
        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)


