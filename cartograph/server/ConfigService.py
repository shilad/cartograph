import json

import falcon

from cartograph import MapConfig


class ConfigService:
    def __init__(self, config):
        self.config = config


    def on_get(self, req, resp):
        js = self.configData()
        resp.status = falcon.HTTP_200
        resp.body = 'var CG = CG || {}; CG.config = ' + json.dumps(js) + ';'
        resp.content_type = 'application/javascript'

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

        result['ColorWheel'] = MapConfig.getColorWheel()
        return result

if __name__ == '__main__':
    conf = MapConfig.initConf('./data/conf/simple.txt')
    svc = ConfigService(conf)
    print svc.configData()

