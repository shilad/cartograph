import os

import falcon

from cartograph.server.ServerUtils import getMimeType


class CacheService:
    def __init__(self, config):
        self.config = config
        self.cacheDir = config.get('DEFAULT', 'webCacheDir')

    def getCachePath(self, req):
        return self.cacheDir +  req.path

    def serveFromCache(self, req, resp):
        try:
            cachePath = self.getCachePath(req)
            resp.stream_len = os.path.getsize(cachePath)
            resp.stream = open(cachePath, 'rb')
            resp.status = falcon.HTTP_200
            resp.content_type = getMimeType(req.path)
            return True
        except OSError:
            return False

    def addToCache(self, req, resp):
        cachePath = self.getCachePath(req)
        d = os.path.dirname(cachePath)
        if not os.path.isdir(d):
            os.makedirs(d)
        with open(cachePath, 'wb') as f:
            f.write(resp.body)
