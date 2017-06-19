# Let's get this party started!
import logging
import os
import sys

import falcon

from cartograph.server.NewMapService import NewMapService
from cartograph.server.utils import add_conf

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

if __name__ == '__main__' and len(sys.argv) > 1:
    confPaths = sys.argv[1]
else:
    confPaths = os.getenv('CARTOGRAPH_CONFIGS')
    if not confPaths:
        raise Exception, 'CARTOGRAPH_CONFIGS environment variable not set!'

configs = {}

logging.info('configuring falcon')

# falcon.API instances are callable WSGI apps
app = falcon.API()

addMapService = NewMapService(app)
app.add_route('/addMap.html', addMapService)

for path in confPaths.split(':'):
    add_conf(path, app)


# Useful for debugging problems in your API; works with pdb.set_trace(). You
# can also use Gunicorn to host your app. Gunicorn can be configured to
# auto-restart workers when it detects a code change, and it also works
# with pdb.
if __name__ == '__main__':
    logging.info('starting server')

    from wsgiref import simple_server
    httpd = simple_server.make_server('127.0.0.1', 4000, app)
    logging.info('server ready!')
    httpd.serve_forever()
