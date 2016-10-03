import logging
import multiprocessing
import os
import tempfile
import threading

import colour

from cartograph.server.CountryService import CountryService

try:
    import cairo
except:
    import cairocffi as cairo

import mapnik
import time

import sys


from multiprocessing import JoinableQueue, Lock

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


    def fromLLtoPixelF(self, ll, zoom):
        d = self.zc[zoom]
        e = d[0] + ll[0] * self.Bc[zoom]
        f = minmax(sin(DEG_TO_RAD * ll[1]), -0.9999, 0.9999)
        g = d[1] + 0.5 * log((1 + f) / (1 - f)) * -self.Cc[zoom]
        return (e, g)

    def fromLLToPixel(self, ll, zoom):
        (e, g) = self.fromLLtoPixelF(ll, zoom)
        return round(e), round(g)

    def fromLLtoTilePixel(self, ll, zoom, tileX, tileY, tileSize):
        # Calculate raw pixel coordinates
        x, y = self.fromLLtoPixelF((ll[0], ll[1]), zoom)

        # px and py are in tile pixel space
        px = (x - tileX * 256)
        py = (y - tileY * 256)

        # Scale up for tile size
        scale = tileSize / 256.0

        return round(px * scale), round(py * scale)


    def fromPixelToLL(self, px, zoom):
        e = self.zc[zoom]
        f = (px[0] - e[0]) / self.Bc[zoom]
        g = (px[1] - e[1]) / -self.Cc[zoom]
        h = RAD_TO_DEG * (2 * atan(exp(g)) - 0.5 * pi)
        return (f, h)


class MapnikService:
    def __init__(self, conf, pointService, countryService):
        self.maps = {}
        self.conf = conf
        self.cache = CacheService(conf)
        self.pointService = pointService
        self.countryService = countryService
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
        surf = self._renderBackground2(z, x, y)
        self._renderPoints(layer, z, x, y, surf)
        surf.write_to_png(path)

    def _renderBackground2(self, z, x, y):
        (polys, points) = self.countryService.getPolys(z, x, y)
        clusterIds = set()
        polysByName = {}
        for pinfo in polys:
            layer, shp, props = pinfo
            if layer == 'countries':
                polysByName[props['clusterid']] = shp
                clusterIds.add(props['clusterid'])
            else:
                assert(layer == 'centroid_contours')
                polysByName[props['clusterid'], int(props['contournum'])] = shp

        numContours = self.conf.getint('PreprocessingConstants', 'num_contours')
        colors = Config.getColorWheel()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.size, self.size)
        context = cairo.Context(surface)
        # First draw clusters
        for i in clusterIds:
            shp = polysByName[i]
            c = colors[i][numContours]
            self._drawPoly(z, x, y, context, shp, c, (0.5, 0.5, 0.5))
            for j in range(numContours):
                if (i, j) in polysByName:
                    shp = polysByName[i, j]
                    c = colors[i][j]
                    self._drawPoly(z, x, y, context, shp, c)
        return surface

    def _drawPoly(self, z, x, y, ctx, shape, fillColor, strokeColor=None):
        if shape.geom_type == 'Polygon': shape = [shape]
        shape = [s for s in shape if s]
        rgb = colour.Color(fillColor).rgb

        def drawRing(ring, reverse=False):
            coords = ring.coords
            if reverse: coords = list(reversed(coords))
            tx, ty = self.tileproj.fromLLtoTilePixel(coords[-1], z, x, y, self.size)
            ctx.move_to(tx, ty)   # start with last point
            for ll in coords:
                tx, ty = self.tileproj.fromLLtoTilePixel(ll, z, x, y, self.size)
                ctx.line_to(tx, ty)

        for poly in shape:
            if poly.exterior.length == 0:
                continue
            ctx.new_path()
            ctx.set_source_rgb(rgb[0], rgb[1], rgb[2])
            drawRing(poly.exterior)
            for hole in poly.interiors:
                drawRing(hole, reverse=True)
            if strokeColor:
                ctx.fill_preserve()
                (r, g, b) = strokeColor
                ctx.set_source_rgb(r, g, b)
                ctx.set_line_width(0.5)
                ctx.stroke()
            else:
                ctx.fill()

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
        (x0, y0, x1, y1) = tileExtent(z, x, y)
        assert(x1 > x0 and y1 > y0)
        metric = self.pointService.metrics[layer]
        cr = cairo.Context(surf)
        cr.fill()

        for p in self.pointService.getTilePoints(z, x, y, 5000):
            xc, yc, = self.tileproj.fromLLtoTilePixel((p['x'], p['y']), z, x, y, self.size)
            (r, g, b, a) = metric.getColor(p, z)
            cr.set_source_rgba(r, g, b, a)
            cr.arc(xc, yc, 1, 0, pi * 2)
            cr.stroke()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    conf = Config.initConf(sys.argv[1])
    ps = PointService(conf)
    cs = CountryService(conf)
    ms = MapnikService(conf, ps, cs)
    t0 = time.time()
    ms.renderTile('gender', 6, 32, 32, 'tile1.png')
    print time.time() - t0
    os.system('open tile1.png')


