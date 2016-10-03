import logging
import marisa_trie

import json
import sys

import falcon

from cartograph.server.ServerUtils import getMimeType

logger = logging.getLogger('cartograph.search')

class SearchService:
    def __init__(self, points):
        self.points = points
        self.keyList = []
        self.tupleLocZoom = []

        self.titleLookupDict = dict()
        self.titles = []
        keys = []
        values = []

        for i, p in enumerate(points.getAllPoints()):
                lowertitle = unicode(p['name'].lower(), 'utf-8')

                self.titles.append(p['name'])
                keys.append(lowertitle)
                values.append((p['zpop'], i, p['x'], p['y'], int(p['id'])))
                if i % 50000 == 0:
                    logging.info('loading autocomplete row %d' % i)

        # after creating lists of all titles and location/zoom, zip them into a trie (will need to extract to json format later)
        fmt = "<diddi"
        self.trie = marisa_trie.RecordTrie(fmt, zip(keys, values))

    def search(self, title, n=10):
        results = sorted(r[1] for r in self.trie.items(unicode(title.lower())))

        # empty list to hold json-formatted results
        jsonList = []

        for (pop, i, x, y, idnum) in results[:n]:
            locat = [y, x]
            rJsonDict = {
                'value' : self.titles[i],
                'data' : { "loc": locat, "zoom": int(pop) }
            }
            jsonList.append(rJsonDict)

        return jsonList

    def on_get(self, req, resp):
        jsonList = self.search(req.params['q'])
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({ 'suggestions' : jsonList })
        resp.content_type = 'application/json'

