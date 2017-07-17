import csv
import os
import json
from ConfigParser import SafeConfigParser
import string
import falcon

from cartograph.Utils import build_map

TYPE_NAME = {'BIVARIATE': 'bivariate-scale', 'COUNT': 'count', 'NONE': None}
COL_PREFIX = 'column_'  # Prefix appended to checkbox form field for a given column


class AddMetricService:
    def __init__(self, conf_path, map_service):
        """
        :param conf_path: path to the config file
        :param map_service: pointer to the map that this service is attached to
        """
        self.conf_path = conf_path
        self.map_service = map_service

    def on_get(self, req, resp):
        config = SafeConfigParser()
        config.read(self.conf_path)

        template = string.Template(open('templates/add_metric.html', 'r').read())

        all_columns = json.loads(config.get('DEFAULT', 'columns'))
        columns_input = ''.join(['<input type="checkbox" name="%s" value="%s"> %s' %
                                (COL_PREFIX+column, column, column) for column in all_columns])

        resp.body = template.substitute(
            columns=columns_input,
            map_name=config.get('DEFAULT', 'dataset')
        )
        resp.content_type = 'text/html'

    def on_post(self, req, resp):

        # Get POST data from request
        post_data = falcon.uri.parse_query_string(req.stream.read())

        # WARNING: this config format normalizes to lowercase in some places but is case-sensitive in others
        metric_name = string.lower(post_data['metric_name'])
        metric_type = TYPE_NAME[post_data['metric_type']]

        # Extract selected columns from the form
        columns = []
        for kw in post_data.keys():
            if kw.startswith(COL_PREFIX):
                columns.append(kw[len(COL_PREFIX):])

        # Extract colors from request
        color_one = post_data['color_one']
        color_two = post_data['color_two']
        neutral_color = post_data['neutral_color']

        # Configure settings for one metric
        metric_settings = {
            'type': metric_type,
            'path': '%(externalDir)s/metric.tsv',
            'fields': columns,
            'colors': [color_one, color_two],
            'percentile': True,  # FIXME: Should the user be able to change this?
            'neutralColor': neutral_color,
            'maxValue': 1.0  # FIXME: Figure out what this does
        }

        # Load map config file
        config = SafeConfigParser()
        config.read(self.conf_path)

        # Combine new metric with previously active metrics
        active_metrics = config.get('Metrics', 'active').split(' ')
        active_metrics.append(metric_name)

        # Add new metric to active metrics list
        config.set('Metrics', 'active', ' '.join(active_metrics))
        config.set('Metrics', metric_name, json.dumps(metric_settings))

        # Save changes to file
        config.write(open(self.conf_path, 'w'))

        # Rebuild the map from the newly-written config file
        build_map(self.conf_path)

        # Mark this map to trigger an update
        self.map_service.trigger_update()
