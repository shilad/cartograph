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
        logDir = config.get('DEFAULT', 'externalDir') + '/logs'
        if not os.path.isdir(logDir):
            try:
                os.makedirs(logDir)
            except OSError: pass

        now = datetime.datetime.now()
        name = re.sub('[^0-9]', '_', now.isoformat()) + '_' + str(random.randrange(100000, 999999)) + '.tsv'
        path = logDir + '/' + name
        print 'logfile is', path
        if not os.path.isfile(path):
            self.log = open(path, 'w')
            return

    def on_post(self, req, resp):
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