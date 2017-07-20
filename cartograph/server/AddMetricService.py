import json
import os
from ConfigParser import SafeConfigParser
import string
import falcon
import pandas

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

    def on_get(self, req, resp, metric_type):

        assert metric_type in {'diverging', 'qualitative', 'sequential'}

        config = SafeConfigParser()
        config.read(self.conf_path)
        all_columns = json.loads(config.get('DEFAULT', 'columns'))
        column_input = ''.join(['<option value="%s" >%s</option>' %
                                 (column, column) for column in all_columns])

        metric_form_template = string.Template(open(os.path.join('templates', '%s_form.html' % metric_type), 'r').read())
        metric_form = metric_form_template.substitute(map_name=self.map_service.name, columns=column_input)

        page_template = string.Template(open('templates/add_metric.html', 'r').read())
        resp.body = page_template.substitute(
            map_name=self.map_service.name,
            metric_form=metric_form
        )
        resp.content_type = 'text/html'

    def on_post(self, req, resp, metric_type):

        # Get POST data from request
        post_data = falcon.uri.parse_query_string(req.stream.read())

        assert metric_type in {'diverging', 'qualitative', 'sequential'}

        # Load map config file
        config = SafeConfigParser()
        config.read(self.conf_path)

        # WARNING: this config format normalizes to lowercase in some places but is case-sensitive in others
        metric_name = string.lower(post_data['metric_name'])

        # Extract colors and column name from request
        palette_name = post_data['color_palette']
        column = post_data['column']

        # Configure settings for a metric
        metric_settings = {
            'type': metric_type,
            'path': '%(externalDir)s/metric.tsv',
            'fields': [column],
            'colorCode': palette_name
        }

        # Add neutral color if client has provided one
        if post_data.has_key('neutral_color'):
            metric_settings['neutralColor'] = post_data['neutral_color']

        # Load user data to mine for appropriate values
        data = pandas.read_csv(os.path.join(config.get('DEFAULT', 'externalDir'), 'metric.tsv'), sep='\t')
        # Add more info to metric settings depending on type
        if metric_type == 'diverging':
            metric_settings.update({
                'maxVal': data[column].max(),
                'minVal': data[column].min()
            })
        elif metric_type == 'qualitative':
            metric_settings.update({
                'scale': list(data[column].unique())
            })
        elif metric_type == 'sequential':
            metric_settings.update({
                'maxValue': data[column].max()
            })

        # Combine new metric with previously active metrics
        active_metrics = config.get('Metrics', 'active').split(' ')
        active_metrics.append(metric_name)
        config.set('Metrics', 'active', ' '.join(active_metrics))

        # Define new metric in config file
        config.set('Metrics', metric_name, json.dumps(metric_settings))

        # Save changes to file
        config.write(open(self.conf_path, 'w'))

        # Rebuild the map from the newly-written config file
        build_map(self.conf_path)

        # Mark this map to trigger an update
        self.map_service.trigger_update()
