import json, os, shutil

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from cartograph.Config import initConf

import Util

import TileStache

# this needs to go away because of new config config = Config.BAD_GET_CONFIG()

def run_server(path_cartograph_cfg, path_tilestache_cfg):
    config = initConf(path_cartograph_cfg)[0]
 
    
    path_tilestache_cfg = os.path.abspath(path_tilestache_cfg)
    path_cache = json.load(open(path_tilestache_cfg, 'r'))['cache']['path']
    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    if os.path.isdir(path_cache):
        assert(len(path_cache) > 5)
        shutil.rmtree(path_cache)

    app = CartographServer(path_tilestache_cfg, config)
    run_simple('0.0.0.0', 8080, app, static_files=static_files)
   
        

#how do i pass config into the cartographserver class?

class CartographServer(TileStache.WSGITileServer):

    def __init__(self, path_cfg, cartograph_cfg):
        TileStache.WSGITileServer.__init__(self, path_cfg)
        self.cartoconfig = cartograph_cfg
      
        xyDict = Util.read_features(self.cartoconfig.get("PostprocessingFiles", "article_coordinates"),
                                         self.cartoconfig.get("PostprocessingFiles", "names_with_id"), self.cartoconfig.get("PreprocessingFiles", "zoom_with_id"))
        self.locList = []

        for entry in xyDict:
            #x and y have to be flipped to get it to match up
            y = float(xyDict[entry]['x'])
            x = float(xyDict[entry]['y'])
            title = xyDict[entry]['name']
            zoom = int(xyDict[entry]['maxZoom'])
            loc = [x, y]
            jsonDict = {"loc": loc, "title": title, "zoom" : zoom}
            self.locList.append(jsonDict)

    def __call__(self, environ, start_response):

        
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic/search'):
            request = Request(environ)

            jsList = []
            title = request.args['q']
            for item in self.locList:
                if item['title'] == title:
                    jsDict = item
                    jsList.append(item)
                    break
            
            response = Response (json.dumps(jsList))
            response.headers['Content-type'] = 'application/json'
           
            return response(environ, start_response)
        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)

    


