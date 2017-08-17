import logging

import json
import sys

import falcon
import shapely.geometry

from cartograph import MapConfig
from cartograph.server.PointService import PointService
from cartograph.server.TopoJson import TopoJsonBuilder

logger = logging.getLogger('cartograph.related')

class RelatednessService:
    def __init__(self, freeText, pointService):
        self.pointService = pointService
        self.freeText = freeText
        self.maxPop = 0
        self.maxCoordinate = 0
        for p in self.pointService.getAllPoints():
            self.maxCoordinate = max(self.maxCoordinate, abs(p['x']), abs(p['y']))
            self.maxPop = max(self.maxPop, p.get('zpop', 0.0))

    def related(self, phrase, n=100):
        results = []
        for id, score in self.freeText.nearestArticlesForPhrase(phrase, n):
            if self.pointService.hasPoint(id):
                p = self.pointService.getPoint(id)
                score *= (self.maxPop + 1.0 - p['zpop']) / (self.maxPop + 1.0)
                results.append((p, score))
        results.sort(key=lambda r: r[1], reverse=True)
        return results

    def on_get(self, req, resp):
        resp.status = falcon.HTTP_200
        builder = TopoJsonBuilder()
        mc = 100
        builder.addPolygon(
            'related-overlay',
            shapely.geometry.box(-mc, -mc, +mc, +mc)
        )
        n = int(req.params['n'])
        results = self.related(req.params['q'], n)
        for i, (p, score) in enumerate(results):
            percentile = (1.0 - 1.0 * i / len(results))
            props = {'score' : score,
                     'name' : p['name'],
                     'percentile' : percentile,
                     'percentile2': percentile ** 2,
                     'fontsize': int(percentile ** 2 * 20)
                     }
            builder.addPoint('related', p['name'],
                             shapely.geometry.Point(p['x'], p['y']), props)
        resp.body = builder.toJson()
        resp.content_type = 'application/json'


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    conf = MapConfig.initConf(sys.argv[1])
    ps = PointService(conf)
    rs = RelatednessService(conf, ps)
    for p, score in rs.related('dog'):
        print p, score