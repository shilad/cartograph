import logging
import multiprocessing
import os

import sys

import time

from cartograph import Config
from cartograph.server.CountryService import CountryService
from cartograph.server.RasterService import RasterService
from cartograph.server.PointService import PointService


class RenderThread:
    def __init__(self, conf, pointService, countryService, q, logLock):
        self.conf = conf
        self.logLog = logLock
        self.q = q
        self.mapnik = RasterService(conf, pointService, countryService)


    def loop(self):
        while True:
            # Fetch a tile from the queue and render it
            r = self.q.get()
            if (r == None):
                self.q.task_done()
                break
            else:
                (name, tile_uri, z, x, y) = r

            if not os.path.isfile(tile_uri):
                t0 = time.time()
                self.mapnik.renderTile(name, z, x, y, tile_uri)
                t1 = time.time()
                self.logLog.acquire()
                logging.info('created %s in %.3f seconds',tile_uri, (t1 - t0))
                self.logLog.release()
            self.q.task_done()

def render(conf):
    pointService = PointService(conf)
    countryService = CountryService(conf)
    maxZoom = conf.getint('Server', 'vector_zoom')
    num_threads = multiprocessing.cpu_count()
    # Launch rendering threads
    queue = multiprocessing.JoinableQueue(32)
    logLock = multiprocessing.Lock()
    renderers = {}
    for i in range(num_threads):
        renderer = RenderThread(conf, pointService, countryService, queue, logLock)
        render_thread = multiprocessing.Process(target=renderer.loop)
        render_thread.start()
        renderers[i] = render_thread

    metric = 'gender'
    cacheDir = conf.get('DEFAULT', 'webCacheDir')
    for z in range(1, maxZoom + 1):
        for x in range(2 ** z):
            for y in range(2 ** z):
                try:
                    path = cacheDir + '/raster/%s/%d/%d/%d.png' % (metric, z, x, y)
                    if not os.path.isfile(path):
                        d = os.path.dirname(path)
                        if d and not os.path.isdir(d): os.makedirs(d)
                        t = (metric, path, z, x, y)
                        queue.put(t)
                except KeyboardInterrupt:
                    raise SystemExit("Ctrl-c detected, exiting...")

    # Signal render threads to exit by sending empty request to queue
    for i in range(num_threads):
        queue.put(None)
    # wait for pending rendering jobs to complete
    queue.join()
    for i in range(num_threads):
        renderers[i].join()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    conf = Config.initConf(sys.argv[1])
    render(conf)
