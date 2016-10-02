import os
import tempfile

import cairo
import mapnik
import time

from cartograph import Config

from math import pi, cos, sin, log, exp, atan

from cartograph.server.CacheService import CacheService
from cartograph.server.PointService import PointService
from cartograph.server.ServerUtils import tileExtent

DEG_TO_RAD = pi / 180
RAD_TO_DEG = 180 / pi


def minmax(a, b, c):
    a = max(a, b)
    a = min(a, c)
    return a

class GoogleProjection:
    def __init__(self, levels=18):
        self.Bc = []
        self.Cc = []
        self.zc = []
        self.Ac = []
        c = 256
        for d in range(0, levels):
            e = c / 2
            self.Bc.append(c / 360.0)
            self.Cc.append(c / (2 * pi))
            self.zc.append((e, e))
            self.Ac.append(c)
            c *= 2

    def fromLLtoPixel(self, ll, zoom):
        d = self.zc[zoom]
        e = round(d[0] + ll[0] * self.Bc[zoom])
        f = minmax(sin(DEG_TO_RAD * ll[1]), -0.9999, 0.9999)
        g = round(d[1] + 0.5 * log((1 + f) / (1 - f)) * -self.Cc[zoom])
        return (e, g)

    def fromPixelToLL(self, px, zoom):
        e = self.zc[zoom]
        f = (px[0] - e[0]) / self.Bc[zoom]
        g = (px[1] - e[1]) / -self.Cc[zoom]
        h = RAD_TO_DEG * (2 * atan(exp(g)) - 0.5 * pi)
        return (f, h)


class MapnikService:
    def __init__(self, conf, pointService):
        self.maps = {}
        self.conf = conf
        self.cache = CacheService(conf)
        self.pointService = pointService
        self.size = 512

        self.xml = os.path.join(self.conf.get('DEFAULT', 'mapDir'), 'base.xml')
        self.m = mapnik.Map(256, 256)
        mapnik.load_map(self.m, self.xml, True)
        self.layers = { l.name : i for (i, l) in enumerate(self.m.layers) }
        assert 'countries' in self.layers
        assert 'contours' in self.layers
        self.prj = mapnik.Projection(self.m.srs)
        self.tileproj = GoogleProjection(19)

    def on_get(self, req, resp, layer, z, x, y):
        z, x, y = map(int, [z, x, y])
        if self.cache.serveFromCache(req, resp):
            return
        path = self.cache.getCachePath(req)
        self.renderTile(layer, z, x, y, path)
        r = self.cache.serveFromCache(req, resp)
        assert(r)

    def renderTile(self, layer, z, x, y, path):
        d = os.path.dirname(path)
        if d and not os.path.isdir(d): os.makedirs(d)
        surf = self._renderBackground(z, x, y)
        self._renderPoints(layer, z, x, y, surf)
        surf.write_to_png(path)

    def _renderBackground(self, z, x, y):

        # Calculate pixel positions of bottom-left & top-right
        p0 = (x * 256, (y + 1) * 256)
        p1 = ((x + 1) * 256, y * 256)

        # Convert to LatLong (EPSG:4326)
        l0 = self.tileproj.fromPixelToLL(p0, z)
        l1 = self.tileproj.fromPixelToLL(p1, z)

        # Convert to map projection (e.g. mercator co-ords EPSG:900913)
        c0 = self.prj.forward(mapnik.Coord(l0[0], l0[1]))
        c1 = self.prj.forward(mapnik.Coord(l1[0], l1[1]))

        # Bounding box for the tile
        bbox = mapnik.Box2d(c0.x, c0.y, c1.x, c1.y)

        render_size = self.size
        self.m.resize(render_size, render_size)
        self.m.zoom_to_box(bbox)
        if self.m.buffer_size < self.size / 2:
            self.m.buffer_size = self.size / 2

        # Render image with default Agg renderer
        n = tempfile.mktemp() + '.png'
        im = mapnik.Image(render_size, render_size)
        mapnik.render(self.m, im)
        im.save(n, 'png256')

        img = cairo.ImageSurface.create_from_png(n)
        os.unlink(n)

        return img

    def _renderPoints(self, layer, z, x, y, surf):
        # Calculate pixel positions of bottom-left & top-right
        p0 = (x * 256, (y + 1) * 256)
        p1 = ((x + 1) * 256, y * 256)

        (x0, y0, x1, y1) = tileExtent(z, x, y)
        assert(x1 > x0 and y1 > y0)
        metric = self.pointService.metrics[layer]
        colors = metric.getColors(z)
        cr = cairo.Context(surf)
        cr.fill()

        for p in self.pointService.getTilePoints(z, x, y, 5000):
            c = self.tileproj.fromLLtoPixel((p['x'], p['y']), z)

            # cx and cy are in pixel space
            xc = (c[0] - x * 256) * 2
            yc = (c[1] - y * 256) * 2

            zp = int(p['zpop'])
            group = metric.assignCategory(p)
            (r, g, b, a) = colors[group][int(zp)]
            cr.set_source_rgba(r, g, b, a)
            cr.arc(xc, yc, 1, 0, pi * 2)
            cr.stroke()
            # cr.set_source_rgba(0.0, 0.0, 0.0, 0.2)
            # cr.stroke()


if __name__ == '__main__':
    conf = Config.initConf('data/conf/simple.txt')
    ps = PointService(conf)
    s = MapnikService(conf, ps)
    t0 = time.time()
    s.renderTile('gender', 2, 1, 1, 'tile1.png')
    print time.time() - t0
    os.system('open tile1.png')



