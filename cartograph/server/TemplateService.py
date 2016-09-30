import os

import falcon
import jinja2

from cartograph.server.ConfigService import ConfigService
from cartograph.server.ServerUtils import getMimeType


class TemplateService:
    def __init__(self, config):
        self.config = config
        self.templateDir = './web/templates'
        self.configService = ConfigService(config)

    def on_get(self, req, resp, file):
        template = self.load_template(file)
        resp.status = falcon.HTTP_200
        resp.content_type = getMimeType(file)
        resp.body = template.render(self.configService.configData())

    def load_template(self, name):
        path = os.path.join(self.templateDir, name)
        with open(os.path.abspath(path), 'r') as fp:
            return jinja2.Template(fp.read())

