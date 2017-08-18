import os

import luigi
import json
import pandas as pd
from cartograph import MapConfig
from cartograph.LuigiUtils import TimestampedLocalTarget, MTimeMixin, getSampleIds

class CreateCategories(luigi.Task):
    def output(self):
        config = MapConfig.get()
        return (TimestampedLocalTarget(config.get("GeneratedFiles", "categories")))

    def run(self):
        config = MapConfig.get()

        # Filter ids
        ids = pd.read_table(config.get("ExternalFiles", "external_ids"), index_col=0)
        ext_to_internal = dict(zip(ids['externalId'], ids.index))

        # Read in the category vector and clean it up
        # Match internal and external IDs and replace them
        colnames = ['externalId'] + list(range(300))
        categories = pd.read_table(config.get("ExternalFiles", "categories"), names=colnames, error_bad_lines=False)
        categories = categories[categories['externalId'].isin(ext_to_internal)]

        # join all vector columns into same column and drop other columns
        categories['category'] = categories.iloc[:, 1:].apply(tuple, axis=1)
        categories.drop(categories.columns[1:-1], axis=1, inplace=True)

        # Reindex on external id
        categories['id'] = categories['externalId'].replace(ext_to_internal)
        categories.set_index('id', inplace=True, drop=True)
        categories.reindex()

        # Change category vector to dictionary
        cat_col = []
        for id, row in categories.iterrows():
            cats = {}
            for s in row['category']:
                if type(s) == str:
                    (k, v) = str(s).split(':')
                    cats[k] = int(v)
            cat_col.append(json.dumps(cats))
        categories['category'] = cat_col

        # Write out category labels
        categories.to_csv(config.get("GeneratedFiles", "categories"), sep='\t', index_label='id',
                          columns=['externalId', 'category'])

    def requires(self):
        return EnsureDirectoriesExist() # This should occur in at least one of the sample tasks


class LabelNames(luigi.Task):
    # FIXME: Replace this by RegionLabel.py tfidf
    '''
    Verify that cluster has been successfully labeled from Java
    and WikiBrain
    '''
    def output(self):
        config = MapConfig.get()
        return (TimestampedLocalTarget(config.get("GeneratedFiles", "region_names")))

    def run(self):
        config = MapConfig.get()

        with open(config.get("GeneratedFiles", "region_names"), 'w') as f:
            f.write('cluster_id\tlabel\n')
            numClusters = config.getint('PreprocessingConstants', 'num_clusters')
            for i in range(numClusters + 1): # +1 is for water cluster
                f.write('%d\tCluster %d\n' % (i, i))
            f.close()

    def requires(self):
        return EnsureDirectoriesExist() # This should occur in at least one of the sample tasks


class ArticlePopularity(luigi.ExternalTask):
    def output(self):
        config = MapConfig.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "popularity")))

class Word2VecFile(luigi.ExternalTask):
    def output(self):
        config = MapConfig.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "w2v")))

class ExternalIdFile(luigi.ExternalTask):
    def output(self):
        config = MapConfig.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles", "external_ids")))

class WikiBrainNumbering(MTimeMixin, luigi.ExternalTask):
    '''
    Number the name and vector output of WikiBrain files so that each
    article has a unique id corrosponding to all of its data for future
    use of any subset of features of interest
    '''

    def output(self):
        config = MapConfig.get()
        return (TimestampedLocalTarget(config.get("ExternalFiles",
                                             "vecs_with_id")),
                TimestampedLocalTarget(config.get("ExternalFiles",
                                             "names_with_id")))


class EnsureDirectoriesExist(luigi.Task):
    def __init__(self, *args, **kwargs):
        super(EnsureDirectoriesExist, self).__init__(*args, **kwargs)
        self.configKeys = ('baseDir', 'externalDir', 'generatedDir', 'geojsonDir', 'mapDir', 'metricDir')

    def output(self):
        config = MapConfig.get()
        return list(
            luigi.LocalTarget(config.get('DEFAULT', n)) for n in self.configKeys
        )

    def requires(self): return []

    def run(self):
        config = MapConfig.get()
        for k in self.configKeys:
            fn = config.get('DEFAULT', k)
            if not os.path.isdir(fn): os.makedirs(fn)


class SampleCreator(MTimeMixin, luigi.Task):
    path = luigi.Parameter()
    prereqs = luigi.Parameter(significant=False, default=[])

    def requires(self):
        # TODO: Require augmented matrix
        from AugmentMatrix import AugmentCluster, AugmentLabel
        return tuple(list(self.prereqs) + [
            WikiBrainNumbering(),
            ArticlePopularity(),
            EnsureDirectoriesExist()
        ])

    def samplePath(self):

        config = MapConfig.get()
        n = config.getint('PreprocessingConstants', 'sample_size')
        return MapConfig.samplePath(self.path, n)

    def output(self):
        return TimestampedLocalTarget(self.samplePath())

    def run(self):
        sampleIds = getSampleIds()
        with open(self.path, 'r') as input, open(self.samplePath(), 'w') as output:
            header = input.readline()
            output.write(header + '\n')
            for line in input:
                id = line.split('\t')[0]
                if id in sampleIds:
                    output.write(line + '\n')