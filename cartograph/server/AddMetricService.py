import json
import os
import string
import falcon
import pandas
from ConfigParser import SafeConfigParser
from cartograph.server.ServerUtils import build_map


class AddMetricService:
    def __init__(self, conf_path, map_service):
        """
        :param conf_path: path to the config file
        :param map_service: pointer to the map that this service is attached to
        """
        self.conf_path = conf_path
        self.map_service = map_service

    def on_post(self, req, resp, metric_type):
        """Add a metric of type <metric_type> to the map stored in self.map_service.

        The POST request should have the follow parameters:
            metric_name: the name for the metric.
            color_palette: the name of the colorbrewer palette to use for metric
            column: the name of the column to be used for this metric
            neutral_color: [optional] the neutral color (e.g. "#00ff88") for this metric
        :param metric_type: str of type of metric (diverging, qualitative, sequential) to be added to map
        :return:
        """

        # Get POST data from request
        post_data = falcon.uri.parse_query_string(req.stream.read())

        if metric_type not in {'diverging', 'qualitative', 'sequential'}:
            raise falcon.HTTPNotFound()

        # Load map config file
        config = SafeConfigParser()
        config.read(self.conf_path)

        # WARNING: this config format normalizes to lowercase in some places but is case-sensitive in others
        metric_name = string.lower(post_data['metric_name'])

        # Extract colors and column name from request
        palette_name = post_data['color_palette']
        column = post_data['column']

        # Combine new metric with previously active metrics
        active_metrics = config.get('Metrics', 'active').split(' ')
        if metric_name in active_metrics:
            resp.body = json.dumps({
                'success': False,
                'map_name': self.map_service.name,
                'error': 'Metric with name "%s" already in map "%s"' % (metric_name, self.map_service.name)
            })
        active_metrics.append(metric_name)
        config.set('Metrics', 'active', ' '.join(active_metrics))

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

        # Define new metric in config file
        config.set('Metrics', metric_name, json.dumps(metric_settings))

        # Save changes to file
        config.write(open(self.conf_path, 'w'))

        # Rebuild the map from the newly-written config file
        build_map(self.conf_path)

        # Mark this map to trigger an update
        self.map_service.trigger_update()
