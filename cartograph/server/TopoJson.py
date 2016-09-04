import json
from collections import OrderedDict


class TopoJsonBuilder:
    def __init__(self):
        self.data = OrderedDict()
        self.data['type'] = 'Topology'
        # self.data["transform"] = {"scale": [1, 1], "translate": [0, 0]}
        self.data["objects"] = OrderedDict()
        for layer in 'countries', 'cities', 'contours':
            self.getCollection(layer)
        self.data["arcs"] = []

    def addPoint(self, collectionName, shapeName, shape, props=None):
        if props == None: props = {}
        props['name'] = shapeName
        coll = self.getCollection(collectionName)

        coll['geometries'].append({
          "type": "Point",
          "properties": props,
          "coordinates": [shape.x, shape.y]
        })

    def addMultiLine(self, collectionName, multiLine, props=None):
        if props == None: props = {}
        coll = self.getCollection(collectionName)
        arcs = []
        for line in multiLine.geoms:
            coords = list(line.coords)
            arcs.append([ self.addArc(coords) ])
        coll['geometries'].append({
            'type': 'MultiLineString',
            'properties' : props,
            'arcs' : arcs
        })

    def addMultiPolygon(self, collectionName, shape, props=None):
        if shape.geom_type == 'Polygon': shape = [shape]
        shape = [s for s in shape if s]
        if not shape:
            return
        if props == None: props = {}
        coll = self.getCollection(collectionName)

        def mkArc(coords):
            coords = list(coords)
            if coords[0] != coords[-1]: # make sure its a ring
                coords = coords + [coords[0]]
            return [ self.addArc(coords) ]

        arcs = []
        for p in shape:
            a = [ mkArc(p.exterior.coords) ]
            for hole in p.interiors:
                a.append(mkArc(hole.coords))
            arcs.append(a)

        coll['geometries'].append({
          "type": "MultiPolygon",
          "properties": props,
          "arcs": arcs
        })

    def addArc(self, arc):
        self.data['arcs'].append(arc)
        return len(self.data['arcs']) - 1

    def toJson(self, filename=None):
        if filename:
            with open(filename, 'w') as f:
                json.dump(self.data, f)
        else:
            return json.dumps(self.data)

    def getCollection(self, name):
        if not name in self.data['objects']:
            self.data['objects'][name] = OrderedDict()
            self.data['objects'][name]['type'] = 'GeometryCollection'
            self.data['objects'][name]['geometries'] = []

        return self.data['objects'][name]