import os

import falcon

from cartograph.server.ServerUtils import getMimeType


class StaticService:
    def __init__(self, config):
        self.config = config
        self.staticDir = './web'

    def on_get(self, req, resp):
        try:
            assert(req.path.startswith('/static'))
            print req.path
            path = self.staticDir + '/' + req.path[7:]
            resp.stream_len = os.path.getsize(path)
            resp.stream = open(path, 'rb')
            resp.status = falcon.HTTP_200
            resp.content_type = getMimeType(req.path)
            return True
        except OSError:
            raise falcon.HTTPNotFound()