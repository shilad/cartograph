import mimetypes

from cartograph.server.MapJobLauncher import build_map
from cartograph.server.globalmaptiles import GlobalMercator

mimetypes.init()

def getMimeType(path):
    if path.endswith('.topojson'):
        return 'application/json'
    elif path.endswith('.yaml'):
        return 'text/plain'
    else:
        (mtype, _) = mimetypes.guess_type(path)
        if mtype:
            return mtype
        else:
            raise Exception, 'Could not infer mimetype for path ' + `path`


_mercator = GlobalMercator()


def tileExtent(z, x, y):
    tx = x
    ty = 2 ** z - 1 - y  # tms coordinates
    (lat0, long0, lat1, long1) = _mercator.TileLatLonBounds(tx, ty, z)
    return (long0, lat0, long1, lat1)


