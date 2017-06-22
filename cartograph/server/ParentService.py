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

    def __getattr__(self, item):
        # Item is the method name

        def func(*args, **kwargs):  # = on_<method>()
                map_name = kwargs['map_name']
                del kwargs['map_name']
                service = self.service_for_map(map_name)
                return getattr(service, item)(*args, **kwargs)

        return func
