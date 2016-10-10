import logging
import os

import colorsys
import tempfile

import colour
import subprocess

from cartograph.server.CountryService import CountryService

try:
    import cairo
except:
    import cairocffi as cairo

import time

import sys


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


class RasterService:
    def __init__(self, conf, pointService, countryService):
        self.maps = {}
        self.conf = conf
        self.cache = CacheService(conf)
        self.pointService = pointService
        self.countryService = countryService
        self.size = 256
        self.tileproj = GoogleProjection(19)
        self.compressPng = conf.getboolean('Server', 'compress_png')

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
        if d and not os.path.isdir(d):
            try: os.makedirs(d)
            except OSError: pass

        surf = self._renderBackground(self.pointService.metrics[layer], z, x, y)
        self._renderPoints(layer, z, x, y, surf)
        self._writePng(surf, path)

    def _writePng(self, surf, pathPng):
        if self.compressPng:
            tmp = tempfile.mktemp()
            surf.write_to_png(tmp)
            dirName = os.path.dirname(pathPng)
            if not os.path.isdir(dirName):
                try: os.makedirs(dirName)
                except OSError: pass    # race condition
            try:
                subprocess.check_call([
                    "pngquant",
                    "--force",
                    "--output",
                    pathPng,
                    "256",
                    "--",
                    tmp
                 ])
            finally:
                os.unlink(tmp)
        else:
            surf.write_to_png(pathPng)


    def _renderBackground(self, metric, z, x, y):
        (polys, points) = self.countryService.getPolys(z, x, y)
        clusterIds = set()
        polysByName = {}
        for pinfo in polys:
            layer, shp, props = pinfo
            if layer == 'countries':
                polysByName[props['clusterId']] = shp
                clusterIds.add(props['clusterId'])
            else:
                assert(layer == 'centroid_contours')
                polysByName[props['clusterId'], int(props['contourNum'])] = shp

        numContours = self.conf.getint('PreprocessingConstants', 'num_contours')
        colors = Config.getColorWheel()
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.size, self.size)
        context = cairo.Context(surface)
        # First draw clusters
        for i in clusterIds:
            shp = polysByName[i]
            c = metric.adjustCountryColor(colors[i][numContours], 0)
            self._drawPoly(z, x, y, context, shp, c, (0.7, 0.7, 0.7))
            for j in range(numContours):
                if (i, j) in polysByName:
                    shp = polysByName[i, j]
                    c = metric.adjustCountryColor(colors[i][j], j + 1)
                    self._drawPoly(z, x, y, context, shp, c)
        return surface

    def _drawPoly(self, z, x, y, ctx, shape, fillColor, strokeColor=None):
        if shape.geom_type == 'Polygon': shape = [shape]
        shape = [s for s in shape if s]
        rgb = fillColor

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
                ctx.set_line_width(1.0)
                ctx.stroke()
            else:
                ctx.fill()

    def _renderPoints(self, layer, z, x, y, surf):
        (x0, y0, x1, y1) = tileExtent(z, x, y)
        assert(x1 > x0 and y1 > y0)
        metric = self.pointService.metrics[layer]
        cr = cairo.Context(surf)
        cr.fill()

        points = self.pointService.getTilePoints(z, x, y, 10000)
        points.sort(key=lambda p: p['zpop'], reverse=True)
        for p in points:
            xc, yc, = self.tileproj.fromLLtoTilePixel((p['x'], p['y']), z, x, y, self.size)
            (r, g, b, a) = metric.getColor(p, z)
            cr.set_source_rgba(r, g, b, a)
            cr.set_line_width(1)
            if z > 7 or (z - p['zpop'] > -1):
                cr.arc(xc, yc, 1, 0, pi * 2)    # two pixels
                cr.stroke()
            else:
                cr.rectangle(xc, yc, 1, 1)
                cr.fill()
                # cr.arc(xc, yc, 0.5, 0, pi * 2)    # two pixels
                # cr.move_to(xc, yc)              # one pixel
                # cr.line_to(xc, yc)


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    conf = Config.initConf(sys.argv[1])
    ps = PointService(conf)
    cs = CountryService(conf)
    ms = RasterService(conf, ps, cs)
    t0 = time.time()
    ms.renderTile('gender', 2, 1, 1, 'tile1.png')
    print time.time() - t0
    print os.path.getsize('tile1.png')
    os.system('open tile1.png')


