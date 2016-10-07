import datetime
import json
import os
import random
import re
import traceback

import falcon


class LoggingService:
    def __init__(self, config):
        self.config = config
        self.logDir = config.get('DEFAULT', 'externalDir') + '/logs'
        if not os.path.isdir(self.logDir):
            try:
                os.makedirs(self.logDir)
            except OSError: pass

        # These are lazily initialized.
        self.path = None
        self.log = None

    def on_post(self, req, resp):
        if not self.path:
            now = datetime.datetime.now()
            name = re.sub('[^0-9]', '_', now.isoformat()) + '_' + str(random.randrange(100000, 999999)) + '.tsv'
            self.path = self.logDir + '/' + name
            assert not os.path.isfile(self.path)
            self.log = open(self.path, 'w')
        try:
            js = json.load(req.stream)
            js['ip'] = req.access_route
            js['agent'] = req.user_agent
            js['uri'] = req.uri
            json.dump(js, self.log)
            self.log.write('\n')
            self.log.flush()    # worry about performance?
        except:
            traceback.print_exc()

        resp.status = falcon.HTTP_200
        resp.body = 'okay'