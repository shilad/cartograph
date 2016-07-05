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

        xyDict = Util.read_features(config.FILE_NAME_ARTICLE_COORDINATES,
                                         config.FILE_NAME_NUMBERED_NAMES)
        locList = []

        for entry in xyDict:
            x = float(xyDict[entry]['x'])
            y = float(xyDict[entry]['y'])
            title = xyDict[entry]['name']
            loc = [x, y]
            jsonDict = {"loc": loc, "title": title}
            locList.append(jsonDict)
        
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic/search'):
            request = Request(environ)

            ''' not using this for now
            jsDict = dict()

            title = request.args['q']
            for item in locList:
                if item['title'] == title:
                    jsDict = item
                    break

       
            title = request.args['q']        

            js = locList            
            
            
            for idnum, valdict in xyDict.items():
                if valdict['name'] == title:
                    x = float(valdict['x'])
                    y = float(valdict['y'])
                    loc = [x, y]
                    name = valdict['name']
                    jsDict = {"loc": loc, "title": name}

                    
            print json.dumps(jsDict)
            '''     

            response = Response (json.dumps(locList))
            response.headers['Content-type'] = 'application/json'
           
            return response(environ, start_response)
        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)


