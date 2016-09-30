import json

import falcon

from cartograph import Config


class ConfigService:
    def __init__(self, config):
        self.config = config


    def on_get(self, req, resp):
        js = self.configData()
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(js)
        resp.content_type = 'application/json'

    def configData(self):
        result = {}
        sections = [
            'PreprocessingConstants',
            'MapConstants',
            'Server',
            'Metrics'
        ]
        for sec in sections:
            result[sec] = {}
            for (key, value) in self.config.items(sec):
                result[sec][key] = value

        for name in result['Metrics']['active'].split():
            result['Metrics'][name]  = json.loads(result['Metrics'][name])

        result['ColorWheel'] = Config.getColorWheel()
        return result

if __name__ == '__main__':
    conf = Config.initConf('./data/conf/simple.txt')
    svc = ConfigService(conf)
    print svc.configData()

