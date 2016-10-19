# A script to replace the tilstache-server.py. 
# It uses our configuration file and also serves static files 
# in web/ under the http://127.0.0.1:8080/static/ URL.
#

import sys
import os

from cartograph.Server import run_server

if len(sys.argv) > 1:
    conf = sys.argv[1]
else:
    conf = "./conf.txt"

if not conf.startswith("/"):
    conf = os.path.abspath(conf)

run_server(conf, os.path.abspath('./data/tilestache.cfg'))
