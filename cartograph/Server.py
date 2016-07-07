import json, os, shutil

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

import Util

import TileStache

# this needs to go away because of new config config = Config.BAD_GET_CONFIG()

def run_server(path_cfg, config):
    config = config
    path_cfg = os.path.abspath(path_cfg)
    path_cache = json.load(open(path_cfg, 'r'))['cache']['path']
    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    if os.path.isdir(path_cache):
        assert(len(path_cache) > 5)
        shutil.rmtree(path_cache)

    app = CartographServer(path_cfg, config)
    run_simple('0.0.0.0', 8080, app, static_files=static_files)
    with open(config.get("PreprocessingConstants", "serverOutput"), "w") as writeFile:
        writeFile.write("Server running")
        

#how do i pass config into the cartographserver class?

class CartographServer(TileStache.WSGITileServer):

    def __init__(self, path_cfg, config):
        self.config = config
        super(CartographServer, self).__init__(path_cfg)

    def __call__(self, environ, start_response):

        xyDict = Util.read_features(config.get("PreprocessingFiles", "article_coordinates"),
                                         config.get("External Files", "names_with_id"))
        locList = []

        for entry in xyDict:
            #x and y have to be flipped to get it to match up
            y = float(xyDict[entry]['x'])
            x = float(xyDict[entry]['y'])
            title = xyDict[entry]['name']
            loc = [x, y]
            jsonDict = {"loc": loc, "title": title}
            locList.append(jsonDict)
        
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic/search'):
            request = Request(environ)

            jsList = []
            title = request.args['q']
            for item in locList:
                if item['title'] == title:
                    jsDict = item
                    jsList.append(item)
                    break
            
            response = Response (json.dumps(jsList))
            response.headers['Content-type'] = 'application/json'
           
            return response(environ, start_response)
        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)

    


