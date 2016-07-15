import json, os, shutil

from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from cartograph.Config import initConf

import marisa_trie

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
      
        xyDict = Util.read_features(self.cartoconfig.get("PreprocessingFiles", "article_coordinates"),
                                         self.cartoconfig.get("PreprocessingFiles", "names_with_id"), self.cartoconfig.get("PreprocessingFiles", "zoom_with_id"))

        self.keyList = []
        self.tupleLocZoom = []


        for entry in xyDict:
            #x and y have to be flipped to get it to match up
            y = float(xyDict[entry]['x'])
            x = float(xyDict[entry]['y'])
            title = xyDict[entry]['name']
            zoom = int(xyDict[entry]['maxZoom'])
            loc = [x, y]
            #second part = add to trie (trying new method for autocomplete)
            locZoom = (x, y, zoom)
            utitle = unicode(title, 'utf-8')
            self.keyList.append(utitle)
            self.tupleLocZoom.append(locZoom)

        #after creating lists of all titles and location/zoom, zip them into a trie (will need to extract to json format later)
        fmt = "<ddi" #a tuple of double, double, int (x, y, zoom
        self.trie = marisa_trie.RecordTrie(fmt, zip(self.keyList, self.tupleLocZoom))

    def __call__(self, environ, start_response):

        
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic/search'):
            request = Request(environ)

            title = request.args['q']
            #trie autocomplete reponse

            results = self.trie.items(unicode(title))

            #empty list to hold json-formatted results
            jsonList = []

            #extract values from tuple in trie
            for item in results:
                titlestring = item[0]
                x = item[1][0]
                y = item[1][1]
                locat = [x,y]
                zoom = item[1][2]
                rJsonDict = {"loc": locat, "title": titlestring, "zoom" : zoom}
                jsonList.append(rJsonDict)
            
            
            response = Response (json.dumps(jsonList))
            response.headers['Content-type'] = 'application/json'
           
            return response(environ, start_response)
        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)

    


