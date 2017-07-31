import json

import falcon

from cartograph.server.CacheService import CacheService
from cartograph.server.TopoJson import TopoJsonBuilder


class TileService:
    def __init__(self, config, pointService, countryService):
        self.config = config
        self.cache = CacheService(config)
        self.pointService = pointService
        self.countryService = countryService

    def getTile(self, layer, z, x, y):
        builder = TopoJsonBuilder()
        self.countryService.addLayers(builder, z, x, y)
        self.pointService.addLayers(builder, layer, z, x, y)
        return builder.getData()

    def on_get(self, req, resp, layer, z, x, y):
        if self.cache.serveFromCache(req, resp):
            return
        z, x, y = int(z), int(x), int(y)
        js = self.getTile(layer, z, x, y)
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(js)
        resp.content_type = 'application/json'
        self.cache.addToCache(req, resp)
