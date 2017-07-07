import os

from cartograph import Config
from cartograph.server.MapService import MapService


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
        :param map_services: a dict mapping names of maps (as strings) to MapService's
        :param service_name: the name (as a string) of the service that this ParentService should provide
        """
        self.map_services = map_services
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
            for map_config in configs:
                map_config_path = map_config.strip('\r\n')

                # If the name of a map isn't in map_services, initialize it
                config = Config.initConf(map_config_path)
                config_name = config.get('DEFAULT', 'dataset')
                if config_name not in self.map_services.keys():
                    map_service = MapService(map_config_path)
                    self.map_services[map_service.name] = map_service

        # indicate that map_services has been updated
        self.map_services['_last_update'] = os.stat(meta_config)

    def __getattr__(self, item):
        # Item is the method name

        def func(*args, **kwargs):  # = on_<method>()

            # Housekeeping: check if the meta-config has been updated; if so, update map_services
            meta_config = self.map_services['_meta_config']
            if os.stat(meta_config) != self.map_services['_last_update']:
                self.update_maps(meta_config)

            # Extract map name from request
            map_name = kwargs['map_name']
            del kwargs['map_name']

            # Return whatever the appropriate service's appropriate method would've returned
            service = self.service_for_map(map_name)
            return getattr(service, item)(*args, **kwargs)

        return func
