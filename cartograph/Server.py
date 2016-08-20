import collections
import json
import marisa_trie
import os
import shutil
from operator import itemgetter

import TileStache
from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response

from cartograph import Utils
from cartograph import Config


def run_server(path_cartograph_cfg):
    Config.initConf(path_cartograph_cfg)
    config = Config.get()

    tsCache = os.path.abspath(config.get('Tilestache', 'cache'))
    tsConfig = os.path.abspath(config.get('Tilestache', 'config'))
    TilestacheConfigurator(config).write(tsConfig)

    static_files =  { '/static': os.path.join(os.path.abspath('./web')) }

    if os.path.isdir(tsCache):
        assert(len(tsCache) > 5)
        shutil.rmtree(tsCache)

    app = CartographServer(tsConfig, config)
    run_simple('0.0.0.0', 8080, app, static_files=static_files)
   

class CartographServer(TileStache.WSGITileServer):

    def __init__(self, path_cfg, cartograph_cfg):
        TileStache.WSGITileServer.__init__(self, path_cfg)
        self.cartoconfig = cartograph_cfg
      
        self.popularityDict = Utils.read_features(
                                    self.cartoconfig.get("ExternalFiles", "names_with_id"),
                                    self.cartoconfig.get("GeneratedFiles","popularity_with_id"))
        xyDict = Utils.read_features(self.cartoconfig.get("GeneratedFiles", "article_coordinates"),
                                     self.cartoconfig.get("ExternalFiles", "names_with_id"),
                                     self.cartoconfig.get("GeneratedFiles", "zoom_with_id"),
                                     required=('x', 'y', 'name', 'maxZoom'))

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

    
class TilestacheConfigurator:
    def __init__(self, config):
        self.config = config

    def makeConfig(self):
        tsConfig = collections.OrderedDict()
        tsConfig['cache'] = self.makeCache()
        tsConfig['layers'] = self.makeLayers()
        return tsConfig

    def write(self, path):
        s = json.dumps(self.makeConfig(), indent=4)
        with open(path, 'w') as f:
            f.write(s)

    def makeCache(self):
        return   {
            "name": "Disk",
            "path": os.path.abspath(self.config.get('Tilestache', 'cache')),
            "verbose": True
          }


    def makeLayers(self):
        layers = collections.OrderedDict()
        scale = 1.0
        tileHeight = 256
        fn = os.path.abspath(self.config.get('MapOutput', 'map_file_centroid'))
        layers['map_density'] = {
            "provider": {"name": "mapnik", "mapfile": "file:" + fn, "scale factor" : scale},
            "projection": "spherical mercator",
            "tile height": tileHeight,
            "metatile": {"rows": 7, "columns": 7, "buffer":120}
        }
        fn = os.path.abspath(self.config.get('MapOutput', 'map_file_density'))
        layers['map_centroid'] = {
            "provider": {"name": "mapnik", "mapfile": "file:" + fn, "scale factor" : scale},
            "projection": "spherical mercator",
            "tile height": tileHeight,
            "metatile": {"rows": 7, "columns": 7, "buffer":120}
        }
        layers['map_countrygrid'] = {
            #"tile height": 512,
            "provider": {
                "class": "TileStache.Goodies.Providers.MapnikGrid:Provider",
                "kwargs": {
                    "mapfile": "file:" + fn,
                    "fields":["labels"],
                    "layer_index": 0,
                    "scale": 4
                }
            }
        }

        # TODO: Make layer indices less fragile by grabbing them from the map xml
        start_layer_index = 4
        start_zoom = 5
        end_zoom = 17
        for zoom in range(start_zoom, end_zoom+1):
            # WHY is this true? Ask Anja Beth
            if zoom < 10:
                fields = ["citylabel", "x", "y"]
            else:
                fields = ["citylabel"]
            layers['map_' + str(zoom) + '_utfgrid'] = {
                #"tile height": 512,
                "provider":
                    {
                        "class": "TileStache.Goodies.Providers.MapnikGrid:Provider",
                        "kwargs":
                            {
                                "mapfile": "file:" + fn,
                                "fields": fields,
                                "layer_index": (end_zoom - zoom) + start_layer_index,
                                "scale": 4
                            }
                    }
            }
        return layers



