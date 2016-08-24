import marisa_trie

import json
import sys


def warn(message):
    sys.stderr.write(message + '\n')

class Search:
    def __init__(self, config, cnx):
        self.config = config
        self.cnx = cnx
        self.keyList = []
        self.tupleLocZoom = []

        self.titleLookupDict = dict()
        self.titles = []
        keys = []
        values = []

        with self.cnx.cursor('autocomplete') as cur:
            cur.itersize = 50000
            cur.execute('select x, y, citylabel, maxzoom, popularity, id from coordinates')
            for i, row in enumerate(cur):
                x = float(row[1])
                y = float(row[0])
                title = row[2]
                zoom = int(row[3])
                pop = float(row[4])
                idnum = int(row[5])

                lowertitle = unicode(title.lower(), 'utf-8')

                self.titles.append(title)
                keys.append(lowertitle)
                values.append((pop, i, x, y, zoom, idnum))
                if i % 50000 == 0:
                    warn('loading autocomplete row %d' % i)

        # after creating lists of all titles and location/zoom, zip them into a trie (will need to extract to json format later)
        fmt = "<diddii"
        self.trie = marisa_trie.RecordTrie(fmt, zip(keys, values))

    def search(self, title, n=10):
        results = sorted(r[1] for r in self.trie.items(unicode(title.lower())))
        results.reverse()

        # empty list to hold json-formatted results
        jsonList = []

        for (pop, i, x, y, zoom, idnum) in results[:n]:
            locat = [x, y]
            rJsonDict = {
                'value' : self.titles[i],
                'data' : { "loc": locat, "zoom": zoom }
            }
            jsonList.append(rJsonDict)

        return json.dumps({ 'suggestions' : jsonList })
