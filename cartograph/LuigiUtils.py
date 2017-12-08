import abc
import json
import logging
import os.path

import luigi
import shapely
import shapely.geometry
import shapely.wkt

import MapConfig, Utils

logger = logging.getLogger('cartograph.luigi')


def to_list(obj):
    if type(obj) in (type(()), type([])):
        return obj
    else:
        return [obj]

class TimestampedLocalTarget(luigi.LocalTarget):
    def mtime(self):
        if not os.path.exists(self.path):
            return -1
        else:
            return int(os.path.getmtime(self.path))

class MTimeMixin:
    '''
    Mixin that flags a task as incomplete if any requirement
    is incomplete or has been updated more recently than this task
    This is based on http://stackoverflow.com/a/29304506, but extends
    it to support multiple input / output dependencies.
    '''
    def complete(self):

        mtimes = [out.mtime() for out in to_list(self.output())]
        if -1 in mtimes:    # something doesn't exist!
            return False
        elif not mtimes:
            return True    # No real output?

        self_mtime = min(mtimes)    # oldest of our outputs  

        for el in to_list(self.requires()):
            if not el.complete():
                return False
            for output in to_list(el.output()):
                if hasattr(output, 'mtime') and output.mtime() > self_mtime:
                    return False
        return True



class ExternalFile(luigi.ExternalTask):
    path = luigi.Parameter()

    def output(self):
        return TimestampedLocalTarget(self.path)


def getSampleIds(n=None):
    config = MapConfig.get()
    # First check if we have an explicitly specified sample
    if config.has_option('ExternalFiles', 'sample_ids') :
        fn = config.get('ExternalFiles', 'sample_ids')
        if fn:
            with open(fn, 'r') as f:
                return set(id.strip() for id in f)

    # If there is no explicit sample, choose one by popularity.

    # Lookup the sample size.
    if n is None:
        n = config.getint('PreprocessingConstants', 'sample_size')
    pops = Utils.read_features(config.get("ExternalFiles", "popularity"))
    tuples = list((float(pops[id]['popularity']), id) for id in pops)
    tuples.sort()
    tuples.reverse()
    return set(id for (pop, id) in tuples[:n])

