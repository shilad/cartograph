from cartograph.metrics.BivariateCountMetric import BivariateCountMetric

def getMetric(js):
    args = dict(js)
    del args['type']
    del args['path']

    mType = js['type']
    if mType == 'bivariate-count':
        return BivariateCountMetric(**args)
    else:
        raise Exception, 'unknown type %s' % `mType`