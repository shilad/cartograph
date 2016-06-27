# A script to replace the tilstache-server.py. 
# It uses our configuration file and also serves static files 
# in web/ under the http://127.0.0.1:8080/static/ URL.
#

import os

from werkzeug.serving import run_simple
import TileStache


import TileStache
app = TileStache.WSGITileServer(os.path.abspath("./data/tilestache.cfg"))
static_files =  { '/static': os.path.join(os.path.abspath('./web')) }
run_simple('0.0.0.0', 8080, app, static_files=static_files)
