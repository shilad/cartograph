import psycopg2

from shapely import wkb

class EdgeLayer:
    def __init__(self, config, cnx):
        self.config = config
        self.cnx = cnx
        self.zoomCutoffs = [
            70, 70, 70, 60, 50,
            40, 30, 20, 15, 12,
            10, 8, 7, 6, 4,
            2, 2, 2,
        ]

    def getEdges(self, extent, zoom):
        query = """
            select bundle, weights, numpoints, endpoints
            from edges
            where numpoints >= %d
            and endPoints && ST_MakeEnvelope%s
        """ % (self.zoomCutoffs[zoom], tuple(extent))

        results = []
        with self.cnx.cursor() as cur:
            cur.itersize = 1000
            print query
            cur.execute(query)
            for row in cur:
                results.append({
                    'bundle' : wkb.loads(row[0], hex=True),
                    'weights' : map(int, row[1].split()),
                    'numpoints' : int(row[2]),
                    'endpoints' : wkb.loads(row[3], hex=True),
                })
        return results

if __name__ == '__main__':
    cnx = psycopg2.connect(dbname='mapnik_simple', host='localhost')
    el = EdgeLayer(None, cnx)
    print el.getEdges([-1.0, -1.0, 0, 0], 8)



