import luigi
from LuigiUtils import MTimeMixin, TimestampedLocalTarget, getSampleIds
from PreReqs import WikiBrainNumbering
import Config

import json
import numpy as np
from sklearn.preprocessing import normalize
import scipy.sparse as sp
import pandas as pd
from sklearn.decomposition import TruncatedSVD

class AugmentLabel(MTimeMixin, luigi.Task):
    '''
    Create an augmented matrix with additional columns composed of an svd on labels.
    '''

    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "vecs_with_labels"))

    def requires(self):
        return WikiBrainNumbering()

    def run(self, label_dims=20, label_weight=0.2):
        config = Config.get()

        # Read in categories
        cat_df = pd.read_table(config.get("ExternalFiles", "categories"), index_col='id')
        vecs_df = pd.read_table(config.get("ExternalFiles", "vecs_with_id"), index_col=0, skiprows=1, header=None)

        # Find dimension and one-hot encoding of sparse matrix
        cat_indexes = {}  # A dictionary of all categories with indices of categories.
        for id, row in cat_df.iterrows():
            for label in json.loads(row['category']):
                if label not in cat_indexes:
                    cat_indexes[label] = len(cat_indexes)

        ncols = len(cat_indexes.keys())
        nrows = cat_df.shape[0]

        # Create a matrix of proper format
        mat = sp.dok_matrix((nrows, ncols), dtype=np.int64)
        for i, (id, row) in enumerate(cat_df.iterrows()):
            for label, value in json.loads(row['category']).items():
                mat[i, cat_indexes[label]] = value
        mat = mat.transpose().tocsr()

        # TruncatedSVD to reduce to dim 20
        svd = TruncatedSVD(n_components=label_dims, n_iter=7, random_state=42)
        svd.fit(mat)
        label_svds = svd.components_.T * label_weight

        # normalize and combine vecs
        vecs_df = vecs_df.div(np.linalg.norm(vecs_df, axis=1), axis=0)
        colnames = ['l_' + str(i) for i in range(label_dims)]
        label_svds = normalize(label_svds, axis=1, norm='l2') * label_weight
        label_df = pd.DataFrame(data=label_svds, columns=colnames, index=cat_df.index.tolist())

        merged = vecs_df.merge(label_df, how='left', left_index=True, right_index=True).fillna(0.0)
        merged.index.rename('id', inplace=True)

        merged.to_csv(config.get("GeneratedFiles", "vecs_with_labels"), sep='\t', index_label='id')


class AugmentCluster(MTimeMixin, luigi.Task):
    '''
    Create an augmented matrix with additional columns composed of one-hot kmeans indicators.
    '''

    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("ExternalFiles", "vecs_with_labels_clusters"))

    def requires(self):
        from Regions import MakeRegions
        return AugmentLabel(), MakeRegions()

    def run(self, clust_weight=0.25):
        config = Config.get()
        cluster_df = pd.read_table(config.get("GeneratedFiles", "clusters_with_id"), index_col='index')
        vecs_with_labels = pd.read_table(config.get("GeneratedFiles", "vecs_with_labels"), index_col=0, skiprows=1, header=None)

        k = np.max(cluster_df['cluster'])  # Number of clusters
        # One-hot encode clusters and write out merged result
        dummy_df = pd.get_dummies(cluster_df, columns=['cluster'], prefix='c') * clust_weight
        merged_df = vecs_with_labels.merge(dummy_df, how='left', left_index=True, right_index=True)

        merged_df.to_csv(config.get("GeneratedFiles", "vecs_with_labels_clusters"), sep='\t', index_label='id')
