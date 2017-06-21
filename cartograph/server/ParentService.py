class ParentService:
    """This is so meta it's making my brain hurt
    """
    def __init__(self, map_services, service_name):
        self.map_services = map_services
        self.service_name = service_name

    def service_for_name(self, map_name):
        return getattr(self.map_services[map_name], self.service_name)

    def __getattr__(self, item):
        # Item is the method name

        def func(*args, **kwargs):  # = on_<method>()
                map_name = kwargs['map_name']
                del kwargs['map_name']
                service = self.service_for_name(map_name)
                return getattr(service, item)(*args, **kwargs)

        return func
