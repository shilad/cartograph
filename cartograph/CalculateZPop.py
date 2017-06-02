import Config
import Utils
import luigi
import Coordinates
from PreReqs import ArticlePopularity
from Regions import MakeRegions
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from geojson import Feature, FeatureCollection
from geojson import dump, Point

import numpy as np

class CalculateZPopCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return (TimestampedLocalTarget(__file__))



class ZPopTask(MTimeMixin, luigi.Task):
    '''
    Calculates an approximate zoom level for every article point in the data,
    i.e. determines when each article label should appear.
    '''
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles",
                                                 "zpop_with_id"))

    def requires(self):
        return (MakeRegions(),
                CalculateZPopCode(),
                Coordinates.CreateFullCoordinates(),
                ArticlePopularity()
                )

    def run(self):
        config = Config.get()
        feats = Utils.read_features(config.get("ExternalFiles",
                                              "popularity"))
        for f in feats.values():
            f['popularity'] = float(f.get('popularity', 0.0))

        def log4(x): return np.log2(x) / np.log2(4)

        ids = list(feats.keys())
        ids.sort(key=lambda i: float(feats[i]['popularity']), reverse=True)
        zpops = list(log4(np.arange(len(ids)) / 2.0 + 1.0))

        Utils.write_tsv(config.get("GeneratedFiles", "zpop_with_id"),
                        ("index", "zpop"), ids, zpops)


def test_zpop_task():
    Config.initTest()

    # Create a unit test config object

    zpt = ZPopTask()
    zpt.run()

    assert zpt is not None



class CoordinatesGeoJSONWriter(MTimeMixin, luigi.Task):
    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("MapData", "coordinates"))

    def requires(self):
        return (
            ZPopTask(),
            Coordinates.CreateFullCoordinates()
        )

    def run(self):

        config = Config.get()
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
            properties = {'id' : id,
                          'zpop': float(pointInfo['zpop']),
                          'name': str(pointInfo['name']),
                          'x': float(pointInfo['x']),
                          'y':float(pointInfo['y']),
                          'clusterid': pointInfo['cluster']
                          }
            features.append(Feature(geometry=newPoint, properties=properties))
        collection = FeatureCollection(features)
        with open(config.get("MapData", "coordinates"), 'w') as f:
            dump(collection, f)