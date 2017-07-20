import json

import numpy as np
import os
import pandas as pd
import shutil

from palettable import colorbrewer

class MetricService:
    def __init__(self, map_services):
        """
        Creates a new service to handle data uploads.
        Args:
            map_services: Dictionary from map name to map
            upload_dir: Absolute full path to map directory
        """
        self.map_services = map_services

    def on_post(self, req, resp):
        resp.body = ''
        map_name = req.get_param('map_name')

        try:
            color_scheme = req.get_param('color_scheme')
            type = req.get_param('type')

            if color_scheme not in dir(getattr(colorbrewer, type)):
                raise ValueError('unknown color scheme: ' + color_scheme)

            resp.body = json.dumps({
                'success': True,
                'title': req.get_param('title'),
                'description': req.get_param('description'),
                'field': req.get_param('field'),
                'type': type,
                'color_scheme': color_scheme,
            })
        except ValueError as e1:
            resp.body = json.dumps({
                'success': False,
                'map_name': map_name,
                'error': str(e1),
                'stacktrace': repr(e1),
            })

        except TypeError as e2:
            resp.body = json.dumps({
                'success': False,
                'map_name': map_name,
                'error': str(e2),
                'stacktrace': repr(e2),
            })