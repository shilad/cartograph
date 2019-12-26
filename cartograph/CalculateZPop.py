import Config
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
        feats = pd.read_table(config.get("ExternalFiles",
                                         "popularity"), index_col='id')
        assert(feats.shape[0]!=0) #check that the popularity data is not empty
        feats = feats.sort_values(by='popularity', ascending=False)

        def log4(x): return np.log2(x) / np.log2(4)

        feats['zpop'] = log4(np.arange(feats.shape[0]) / 2.0 + 1.0)
        feats['zpop'].to_csv(config.get("GeneratedFiles", "zpop_with_id"), sep='\t', index_label='index', header='zpop')


def test_zpop_task():
    config = Config.initTest()
    # Create a unit test config object
    zpt = ZPopTask()
    zpt.run()

    # Ordering should be the same.
    ptable = pd.read_table(config.get("ExternalFiles", "popularity"))
    ztable = pd.read_table(config.get("GeneratedFiles", "zpop_with_id"))
    ptable = ptable.sort_values('popularity', ascending=False)
    ztable = ztable.sort_values('zpop', ascending=True)
    assert ptable['id'].tolist() == ztable['index'].tolist()
