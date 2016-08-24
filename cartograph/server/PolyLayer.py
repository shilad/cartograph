import shapely.geometry
import shapely.wkb


class PolyLayer:
    def __init__(self, name, table=None, fields=None, simplification=None, labelField=None):
        assert(table and fields and simplification)
        self.name = name
        self.table = table
        self.fields = fields
        self.simplification = simplification
        self.labelField = labelField
        self.cache = {}

    def getFromCache(self, cur, z):
        z = self.getEffectiveZoom(z)
        if not z in self.cache:
            query = 'select %s from %s' % (', ' .join(['geom'] + self.fields), self.table)
            cur.execute(query)
            raw = []
            props = []
            for row in cur:
                props.append(dict(zip(self.fields, row[1:])))
                raw.append(shapely.wkb.loads(row[0], hex=True).buffer(0))
            merged = shapely.geometry.GeometryCollection(raw)
            # simplified = list(merged)
            simplified = list(s.buffer(0) for s in merged.simplify(self.simplification[z]))
            centers = list(s.representative_point() for s in simplified)
            self.cache[z] = zip(simplified, props, centers)
        return self.cache[z]

    def getPolys(self, cur, z):
        polys = self.getFromCache(cur, z)
        result = []
        for shp, prop, center in polys:
            p = dict(prop)
            result.append((
                shp,
                p,
                center
            ))
        return result

    def getPolysInBox(self, cur, z, box):
        polys = self.getFromCache(cur, z)
        result = []
        for shp, prop, center in polys:
            if box.intersects(shp):
                p = dict(prop)
                result.append((
                    box.intersection(shp),
                    p,
                    center if box.contains(center) else None
                ))
        return result


    def getEffectiveZoom(self, z):
        """Returns the highest known zoom that is less than or equal to z"""
        effectiveZ = min(self.simplification.keys())
        for i in range(z+1):
            if i in self.simplification:
                effectiveZ = i
        return effectiveZ