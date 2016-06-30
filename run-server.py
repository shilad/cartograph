# A script to replace the tilstache-server.py. 
# It uses our configuration file and also serves static files 
# in web/ under the http://127.0.0.1:8080/static/ URL.
#

import os

from cartograph.Server import run_server

run_server(os.path.abspath('./data/tilestache.cfg'))
