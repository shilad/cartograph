# A script to replace the tilstache-server.py. 
# It uses our configuration file and also serves static files 
# in web/ under the http://127.0.0.1:8080/static/ URL.
#

import json, os, shutil

from werkzeug.serving import run_simple
import TileStache


static_files =  { '/static': os.path.join(os.path.abspath('./web')) }
path_cfg = os.path.abspath("./data/tilestache.cfg")
path_cache = json.load(open(path_cfg, 'r'))['cache']['path']

if os.path.isdir(path_cache):
    assert(len(path_cache) > 5)
    shutil.rmtree(path_cache)

app = TileStache.WSGITileServer(path_cfg)

run_simple('0.0.0.0', 8080, app, static_files=static_files)
