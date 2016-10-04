from cartograph.metrics.BivariateCountMetric import BivariateCountMetric
from cartograph.metrics.BivariateScaleMetric import BivariateScaleMetric


def getMetric(js):
    args = dict(js)
    del args['type']
    del args['path']

    mType = js['type']
    if mType == 'bivariate-count':
        return BivariateCountMetric(**args)
    if mType == 'bivariate-scale':
        return BivariateScaleMetric(**args)
    else:
        raise Exception, 'unknown type %s' % `mType`