import json

import falcon

from cartograph import MapConfig

import palettable.colorbrewer.sequential as sq
import palettable.colorbrewer.diverging as dv
import palettable.colorbrewer.qualitative as qu


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
            'DEFAULT'
        ]
        for sec in sections:
            result[sec] = {}
            for (key, value) in self.config.items(sec):
                result[sec][key] = value

        result['Metrics'] = {}
        for name in self.config.get('Metrics', 'active').split():
            m = json.loads(self.config.get('Metrics', name))
            c = m['colorscheme']
            if hasattr(sq, c):
                m['palette'] = getattr(sq, c)
            elif hasattr(dv, c):
                m['palette'] = getattr(dv, c)
            elif hasattr(qu, c):
                m['palette'] = getattr(qu, c)
            else:
                raise Exception("Unknown color palette: " + c)
            result['Metrics'][name]  = m

        result['ColorWheel'] = MapConfig.getColorWheel()
        return result

if __name__ == '__main__':
    conf = MapConfig.initConf('./data/conf/simple.txt')
    svc = ConfigService(conf)
    print svc.configData()

