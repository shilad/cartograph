import json, os, shutil

from operator import itemgetter
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from cartograph.Config import initConf

import marisa_trie

import Util

import TileStache


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
   

class CartographServer(TileStache.WSGITileServer):

    def __init__(self, path_cfg, cartograph_cfg):
        TileStache.WSGITileServer.__init__(self, path_cfg)
        self.cartoconfig = cartograph_cfg
      
        xyDict = Util.read_features(self.cartoconfig.get("PreprocessingFiles", "article_coordinates"),
                                         self.cartoconfig.get("PreprocessingFiles", "names_with_id"), self.cartoconfig.get("PreprocessingFiles", "zoom_with_id"))
        self.popularityDict = Util.read_features(self.cartoconfig.get("PreprocessingFiles", "names_with_id"), self.cartoconfig.get("PreprocessingFiles","popularity_with_id"))

        self.keyList = []
        self.tupleLocZoom = []

        self.titleLookupDict = dict()

        for entry in xyDict:
            #x and y have to be flipped to get it to match up
            y = float(xyDict[entry]['x'])
            x = float(xyDict[entry]['y'])
            title = xyDict[entry]['name']
            self.titleLookupDict[entry] = title
            zoom = int(xyDict[entry]['maxZoom'])
            loc = [x, y]
            idnum = int(entry)
            #second part = add to trie (trying new method for autocomplete)
            locZoom = (x, y, zoom, idnum)
            lowertitle = unicode(title.lower(), 'utf-8')
           
            self.keyList.append(lowertitle)
            self.tupleLocZoom.append(locZoom)

        #after creating lists of all titles and location/zoom, zip them into a trie (will need to extract to json format later)
        fmt = "<ddii" #a tuple of double, double, int, string (x, y, zoom, regular case title)
        self.trie = marisa_trie.RecordTrie(fmt, zip(self.keyList, self.tupleLocZoom))

    def __call__(self, environ, start_response):
        
        path_info = environ.get('PATH_INFO', None)
        if path_info.startswith('/dynamic/search'):
                request = Request(environ)

                title = request.args['q']
                
                #trie autocomplete reponse

                results = self.trie.items(unicode(title))

                #empty list to hold tuples to sort - TODO
                tupleList = []
                #empty list to hold json-formatted results
                jsonList = []

                #extract values from tuple in trie
                for item in results:
                    idnum = str(item[1][3])
                    titlestring = self.titleLookupDict[idnum]
                    pop = float(self.popularityDict[idnum]['popularity'])
                    x = item[1][0]
                    y = item[1][1]
                    locat = [x,y]
                    zoom = item[1][2]
                    itemTuple = (locat, zoom, titlestring, pop)
                    tupleList.append(itemTuple)

                sortedTupleList = sorted(tupleList, key=itemgetter(3))
                sortedTupleList.reverse()

                for item in sortedTupleList:
                    locat = item[0]
                    zoom = item[1]
                    titlestring = item[2]
                    rJsonDict = {"loc": locat, "title": titlestring, "zoom" : zoom}
                    jsonList.append(rJsonDict)
                
                
                response = Response (json.dumps(jsonList))
                response.headers['Content-type'] = 'application/json'
               
                return response(environ, start_response)
            

        else:
            return TileStache.WSGITileServer.__call__(self, environ, start_response)

    


