import json

import shapely.geometry
import shapely.wkb


class PolyLayer:
    def __init__(self, name, path=None, fields=None, simplification=None, labelField=None):
        assert(path and fields and simplification)
        self.name = name
        self.path = path
        self.fields = fields
        self.simplification = simplification
        self.labelField = labelField
        self.cache = {}

    def init(self):
        with open(self.path, 'r') as f:
            js = json.load(f)

        rows = []
        for geomJS in js['features']:
            r = {}
            r['geometry'] = shapely.geometry.shape(geomJS['geometry'])
            r.update(geomJS.get('properties', {}))
            rows.append(r)

        for z in range(1, 20):
            z = self.getEffectiveZoom(z)
            if z in self.cache: continue

            raw = []
            props = []
            for row in rows:
                props.append({ k : v for (k, v) in row.items() if k != 'geometry' })
                raw.append(row['geometry'].buffer(0))
            merged = shapely.geometry.GeometryCollection(raw)
            # simplified = list(merged)
            simplified = list(s.buffer(0) for s in merged.simplify(self.simplification[z]))
            centers = list(s.representative_point() for s in simplified)
            self.cache[z] = zip(simplified, props, centers)

    def getFromCache(self, z):
        z = self.getEffectiveZoom(z)
        assert(z in self.cache)
        return self.cache[z]

    def getPolys(self, z):
        polys = self.getFromCache(z)
        result = []
        for shp, prop, center in polys:
            p = dict(prop)
            result.append((
                shp,
                p,
                center
            ))
        return result

    def getPolysInBox(self, z, box):
        polys = self.getFromCache(z)
        result = []
        for shp, prop, center in polys:
            if box.intersects(shp):
                c = center if box.contains(center) else None
                p = dict(prop)
                result.append((
                    box.intersection(shp),
                    p,
                    c
                ))
        return result


    def getEffectiveZoom(self, z):
        """Returns the highest known zoom that is less than or equal to z"""
        effectiveZ = min(self.simplification.keys())
        for i in range(z+1):
            if i in self.simplification:
                effectiveZ = i
        return effectiveZ