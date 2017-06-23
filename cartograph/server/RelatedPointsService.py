import logging

import json

import falcon

logger = logging.getLogger('cartograph.point')



class RelatedPointsService:
    def __init__(self, config, points):
        self.config = config
        self.points = points
        pointsdict = {} #pointsdict is a dictionary where the key is an article's id and the value is its x,y coordinates.
        for p in points.getAllPoints():
            k = p['id']
            value = [p['id'], p['name'], p['x'], p['y']]
            pointsdict[k] = value
        d = {}  # d is a dictionary where the key is an article id and the value is a list of all its related articles' x,y coordinates.
        with open("./data/ext/simple/links.tsv") as f: #opens tsv file
            f.next() #skips over header line
            for line in f: #reads over each line
                row = str(line).split() #creates an array where each column is a value
                key = row[0] #makes the key the first item in the array
                list = row[:] #makes a list of the rest of values in the array
                valuelist = []
                for item in list:
                    try:
                        valuelist.append(pointsdict[item])
                    except Exception, e:
                        if 'KeyError' in str(e):
                            continue
                val = valuelist
                d[key] = val

        self.d = d
        self.pointsdict = pointsdict

    def getPointCoord(self, id): #talk to shilad about try/except error ALSO this gives back the X,Y coord of a specific article and might be used as a key?? for now, not tho
        try:
            return self.pointsdict[id]
        except Exception, e:
            if id in str(e): #why is the error the id???
                return "Location of Selected Article Unknown"

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
        return jsonList #jsonList in right format?

    def on_get(self, req, resp):
        relatedPoints = self.getRelatedPoints(req.params['id'])
        resp.status = falcon.HTTP_200
        resp.body = json.dumps({req.params['id']: relatedPoints})
        resp.content_type = 'application/json'