import MapConfig
import Utils
import luigi
import Coordinates
from PreReqs import ArticlePopularity
from Regions import MakeRegions
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from geojson import Feature, FeatureCollection
from geojson import dump, Point
import filecmp

import numpy as np
import pandas as pd

class CalculateZPopCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))



class ZPopTask(MTimeMixin, luigi.Task):
    '''
    Calculates an approximate zoom level for every article point in the data,
    i.e. determines when each article label should appear.
    '''
    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles",
                                                 "zpop_with_id"))

    def requires(self):
        return (MakeRegions(),
                CalculateZPopCode(),
                Coordinates.CreateFullCoordinates(),
                ArticlePopularity()
                )

    def run(self):
        config = MapConfig.get()
        feats = pd.read_table(config.get("ExternalFiles",
                                         "popularity"), index_col='id')
        assert(feats.shape[0]!=0) #check that the popularity data is not empty
        feats = feats.sort_values(by='popularity', ascending=False)

        def log4(x): return np.log2(x) / np.log2(4)

        feats['zpop'] = log4(np.arange(feats.shape[0]) / 2.0 + 1.0)
        feats['zpop'].to_csv(config.get("GeneratedFiles", "zpop_with_id"), sep='\t', index_label='index', header='zpop')


def test_zpop_task():
    config = MapConfig.initTest()
    # Create a unit test config object
    zpt = ZPopTask()
    zpt.run()

    # Ordering should be the same.
    ptable = pd.read_table(config.get("ExternalFiles", "popularity"))
    ztable = pd.read_table(config.get("GeneratedFiles", "zpop_with_id"))
    ptable = ptable.sort_values('popularity', ascending=False)
    ztable = ztable.sort_values('zpop', ascending=True)
    assert ptable['id'].tolist() == ztable['index'].tolist()


#Is this used at all?
class CoordinatesGeoJSONWriter(MTimeMixin, luigi.Task):
    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("MapData", "coordinates"))

    def requires(self):
        return (
            ZPopTask(),
            Coordinates.CreateFullCoordinates()
        )

    def run(self):
        config = MapConfig.get()
        points = Utils.read_features(
            config.get("GeneratedFiles", "zpop_with_id"),
            config.get("GeneratedFiles", "article_coordinates"),
            config.get("GeneratedFiles", "clusters_with_id"),
            config.get("ExternalFiles", "names_with_id"),
            required=('x', 'y', 'name', 'zpop', 'cluster')
        )

        features = []
        for id, pointInfo in points.items():
            pointTuple = (float(pointInfo['x']), float(pointInfo['y']))
            newPoint = Point(pointTuple)
            properties = {'id': id,
                          'zpop': float(pointInfo['zpop']),
                          'name': str(pointInfo['name']),
                          'x': float(pointInfo['x']),
                          'y': float(pointInfo['y']),
                          'clusterid': pointInfo['cluster']
                          }
            features.append(Feature(geometry=newPoint, properties=properties))
        collection = FeatureCollection(features)
        with open(config.get("MapData", "coordinates"), 'w') as f:
            dump(collection, f)
