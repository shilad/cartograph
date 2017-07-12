import os
import re

from cartograph import Config
from cartograph.server.MapService import MapService


METACONF_FLAG = '######'  # TODO: Find a better home for this constant


class ParentService:
    """A ParentService represents a given service (specified by <service_name>) for every map in <map_services>.

    example:
    parent_logging_service = ParentService(map_services, 'logging_service')  # map_services is a dict of

    Now, when you call parent_logging_service.on_get(*args, **kwargs) (or .on_post(), or any other method), it will look
    for the kwarg <map_name> in kwargs to determine which MapService in <map_services> to use, then it will call that
    MapService's .logging_service.on_get(*args, **kwargs).
    """
    def __init__(self, map_services, service_name):
        """
        :param map_services: a dict mapping names of maps (as strings) to MapService's; this should point to *one* copy
                             of map_services shared across the whole server.
        :param service_name: the name (as a string) of the service that this ParentService should provide
        """
        self.map_services = map_services  # Points to singleton instance of a dictionary of names to MapServices;
        self.service_name = service_name

    def service_for_map(self, map_name):
        """Get the service (as specified by self.service_name) for the map specified in <map_name>
        :param map_name: the name of the map for which to return the service
        :return: The service (as specified by self.service_name) for the map specified by <map_name>
        """
        return getattr(self.map_services[map_name], self.service_name)

    def update_maps(self, meta_config):
        """Initialize any map whose map-config is in the meta-config, but has not yet been initialized.
        :return:
        """
        with open(meta_config, 'r') as configs:
            assert configs.readline().strip('\r\n') == METACONF_FLAG  # Check/skip the multi-map flag
            for map_config in re.split('[\\r\\n]+', configs.read()):

                # If it's a blank line, ignore it
                if map_config == '':
                    continue

                map_name = Config.initConf(map_config).get('DEFAULT', 'dataset')

                # If the name of a map isn't in map_services, initialize it
                if map_name not in self.map_services.keys():
                    map_service = MapService(map_config)
                    self.map_services[map_service.name] = map_service

                # If the config file has been updated, start a new MapService for it
                if os.path.getmtime(map_config) != self.map_services[map_name].last_update:
                    self.map_services[map_name] = MapService(map_config)

        # indicate that map_services has been updated
        self.map_services['_last_update'] = os.path.getmtime(meta_config)

    def __getattr__(self, item):
        """
        :param item: name of method (e.g. "on_get")
        :return: the method
        """

        def func(*args, **kwargs):  # = on_<method>()

            # Housekeeping: make sure maps are updated
            meta_config = self.map_services['_meta_config']
            if self.map_services['_multi_map']:

                # if a map has requested an update, change mod time of the meta-config file, which should trigger (via
                # self.update_maps) an update of all maps whose config files have changed.
                for map_name in self.map_services.keys():
                    if (not map_name.startswith('_')) and self.map_services[map_name].needs_update():
                            os.utime(meta_config, None)

                # if the meta-config has been updated, update (server-wide dict) map_services
                if os.path.getmtime(meta_config) != self.map_services['_last_update']:
                    self.update_maps(meta_config)

            # Now, process the request:
            # Extract map name from request
            map_name = kwargs['map_name']
            del kwargs['map_name']

            # Return whatever the appropriate service's appropriate method would've returned
            service = self.service_for_map(map_name)
            return getattr(service, item)(*args, **kwargs)

        return func
