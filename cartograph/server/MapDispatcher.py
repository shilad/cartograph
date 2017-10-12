import os
import logging

import falcon

from cartograph.server.AddMapService2 import get_build_status, STATUS_SUCCEEDED, get_status_path
from cartograph.server.Map import Map


class RouteStub:
    def __init__(self, dispatcher, service_name):
        self.dispatcher = dispatcher
        self.service_name = service_name

    def on_get(self, *args, **kwargs):
        return self.dispatcher.on_get(self.service_name, *args, **kwargs)

    def on_post(self, *args, **kwargs):
        return self.dispatcher.on_post(self.service_name, *args, **kwargs)

class MapDispatcher:
    def __init__(self, app, server_config, meta_path):
        assert os.path.isfile(meta_path)

        self.app = app
        self.meta_path = meta_path
        self.tstamp = -1
        self.conf = server_config
        self.maps = {}
        self.map_paths = set()
        self.added_names = set()    # names we have added to the config already

        self.check_config()

    def get_maps(self):
        return self.maps

    def has_map(self, map_id):
        return map_id in self.maps

    def add_route(self, route, service_name):
        self.app.add_route(route, RouteStub(self, service_name))

    def add_sink(self, prefix, service_name):
        self.app.add_sink(RouteStub(self, service_name).on_get, prefix)

    def on_get(self, service_name, req, resp, map_name, *args, **kwargs):
        map = self.get_map(map_name)
        self.check_config()
        getattr(map, service_name).on_get(req, resp, *args, **kwargs)

    def on_post(self, service_name, req, resp, map_name, *args, **kwargs):
        map = self.get_map(map_name)
        self.check_config()
        getattr(map, service_name).on_post(req, resp, *args, **kwargs)

    def get_map(self, map_name, attempt_num=0):

        if map_name in self.maps:
            return self.maps[map_name]
        elif attempt_num == 0 and map_name not in self.added_names:
            # Check to see if a build of the requested map has finished
            # If it has, add the config line to the meta config file and
            # Recall the function, triggering a check_config() and reload.
            # Note that we record that we added the map to prevent spinning
            # if the loading of the map fails for some reason.
            status = get_build_status(self.conf, map_name)
            if status == STATUS_SUCCEEDED:
                with open(self.meta_path, 'a') as f:
                    f.write(get_status_path(self.conf, map_name) + '\n')
                self.added_names.add(map_name)
                self.check_config()
                return self.get_map(map_name, attempt_num + 1)

        raise falcon.HTTPNotFound(title='Map not found',
                                  description='No map found named ' + repr(map_name))

    def check_config(self):
        """
        Check whether the internal maps are up to date with the meta config.
        More specifically, check the timestamp associated with the meta config and
        see if we have already read it.
        """
        ts = os.path.getmtime(self.meta_path)
        if ts <= self.tstamp:
            return  # Up to date

        for path in (line.strip() for line in open(self.meta_path)):
            if path and path not in self.map_paths:
                try:
                    map = Map(path)
                    self.maps[map.name] = map
                    self.map_paths.add(path)
                except:
                    logging.exception('Failed to load map ' + repr(path))

        self.tstamp = ts