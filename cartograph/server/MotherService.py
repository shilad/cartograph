class ParentService:
    """This is so meta it's making my brain hurt
    """
    def __init__(self, map_services, service_name):
        self.map_services = map_services
        self.service_name = service_name

    def __getattr__(self, item):
        # Item is the method name

        def func(self, name, *args, **kwargs):  # on_method()
                return self.map_services[name].__getattr__(self.service_name).__getattr__(item)

        return func
