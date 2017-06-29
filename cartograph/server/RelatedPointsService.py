import logging

import json

import falcon

logger = logging.getLogger('cartograph.relatedpoint')


class RelatedPointsService:
    def __init__(self, config, points):
        self.config = config
        self.points = points
        pointsdict = {p['id']: [p['id'], p['name'], p['x'], p['y']] for p in points.getAllPoints()} #pointsdict is a dictionary where the key is an article's id and the value is its x,y coordinates.
        d = {}  # d is a dictionary where the key is an article id and the value is a list of all its related articles' x,y coordinates.
        with open("./data/ext/simple/links.tsv") as f: #opens tsv file
            f.next() #skips over header line
            for line in f: #reads over each line
                row = str(line).split() #creates an array where each column is a value
                id, links = row[0], row[:]
                d[id] = [pointsdict[i] for i in links if i in pointsdict]

        self.d = d
        self.pointsdict = pointsdict


    def getRelatedPoints(self, id):
        # empty list to hold json-formatted results
        jsonList = []

        for list in self.d[id]:
            locat = [list[3], list[2]]
            rJsonDict = {
                'type': 'concept',
                'data': {"id": list[0], "name": list[1], "loc": locat}
            }
            jsonList.append(rJsonDict)
        return jsonList

    def on_get(self, req, resp):
        relatedPoints = self.getRelatedPoints(req.params['id'])
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({req.params['id']: relatedPoints})
        resp.content_type = 'application/json'