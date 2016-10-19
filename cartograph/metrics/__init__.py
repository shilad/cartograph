from cartograph.metrics.BivariateCountMetric import BivariateCountMetric
from cartograph.metrics.BivariateScaleMetric import BivariateScaleMetric
from cartograph.metrics.BivariateNominalMetric import BivariateNominalMetric
from cartograph.metrics.TrivariateCountMetric import TrivariateCountMetric


def getMetric(js):
    args = dict(js)
    del args['type']
    del args['path']

    mType = js['type']
    if mType == 'trivariate-count':
        return TrivariateCountMetric(**args)
    elif mType == 'bivariate-count':
        return BivariateCountMetric(**args)
    elif mType == 'bivariate-scale':
        return BivariateScaleMetric(**args)
    elif mType == 'bivariate-nominal':
        return BivariateNominalMetric(**args)
    else:
        raise Exception, 'unknown type %s' % `mType`