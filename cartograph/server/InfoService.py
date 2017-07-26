import json


class InfoService:
    def __init__(self, conf):
        self.conf = conf

    def on_get(self, req, resp):
        active_metrics = self.conf.get('Metrics', 'active').split(' ')
        metrics_info = {}
        for metric_name in active_metrics:
            metric_settings = json.loads(self.conf.get('Metrics', metric_name))
            metrics_info[metric_name] = metric_settings
        resp.body = json.dumps({
            'metrics': metrics_info
        })
        resp.content_type = 'application/json'