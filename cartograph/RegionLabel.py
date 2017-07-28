from collections import defaultdict
import pandas as pd
import ast
import luigi
from LuigiUtils import MTimeMixin, TimestampedLocalTarget
from PreReqs import EnsureDirectoriesExist
from AugmentMatrix import AugmentCluster
from cartograph import Config
import logging


class RegionLabel(MTimeMixin, luigi.Task):
    '''
    Label the clusters with TF-IDF method
    '''

    def output(self):
        config = Config.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "region_names"))

    def requires(self):
        return (EnsureDirectoriesExist(),
                AugmentCluster())

    def run(self):
        # Calculate TF-IDF scores
        config = Config.get()
        category_df = pd.read_table(config.get("GeneratedFiles", "categories"), index_col='id')
        cluster_df = pd.read_table(config.get("GeneratedFiles", "clusters_with_id"), index_col='index')

        docScores = []  # Nested list of tf-idf scores per document
        catCounts = defaultdict(int)
        for i, (id, row) in enumerate(category_df.iterrows()):
            catDict = ast.literal_eval(row['category'])
            for key in catDict:
                catCounts[key] += 1

        for i, (_, row) in enumerate(category_df.iterrows()):
            if i % 10000 == 0: logging.info('Calculated TF-IDF for {}/{}'.format(i, len(category_df)))
            catDict = ast.literal_eval(row['category'])
            for key, tf in catDict.items():
                df = catCounts[key]
                # catDict[key] = tf * math.log(len(allGraphDict) / df)
                catDict[key] = tf * (1.0 * len(category_df) / df)
                # catDict[key] = tf * (1.0 * len(allGraphDict) / df) ** 0.5
            docScores.append(sorted(catDict.items(), key=lambda x: x[1], reverse=True))

        # Save tf-idf scores as a data frame
        score_df = pd.DataFrame({'id': category_df.index, 'score': docScores})
        score_df.set_index('id', inplace=True)

        # Choose label for each cluster
        candidateLabel = []  # Nested array for best labels per cluster
        cluster = []
        for i in cluster_df['cluster'].unique():
            logging.info("Finding label for cluster {}".format(i))
            cluster.append(i)
            idCluster = cluster_df.loc[cluster_df['cluster'] == i].index  # Get all id of nodes in a cluster
            bestScore = 0
            bestLabel = None
            totalLabel = {}
            for id in idCluster:
                if id in score_df.index:
                    # Sum up tfidf scores for all articles in the  cluster, select labels with highest score
                    for label in score_df.loc[id]['score']:
                        if label[0] in totalLabel.keys():
                            totalLabel[label[0]][0] += label[1]  # Sum up tfidf scores
                            totalLabel[label[0]][1] += 1  # Number of occurrences of this label
                        else:
                            totalLabel[label[0]] = [label[1]]
                            totalLabel[label[0]].append(1)
                        if bestScore < totalLabel[label[0]][0] * totalLabel[label[0]][1]:
                            bestScore = totalLabel[label[0]][0] * totalLabel[label[0]][1]
                            bestLabel = label[0]

            # totalLabel = sorted(totalLabel.items(), key=lambda x: x[1][1] * x[1][0], reverse=True)
            candidateLabel.append(bestLabel)  # Choose the label with the highest tf-idf score

        label_df = pd.DataFrame({'cluster_id': cluster, 'label': candidateLabel})
        label_df.set_index('cluster_id', inplace=True)
        label_df.sort_index(inplace=True)
        label_df.to_csv(config.get("GeneratedFiles", "region_names"), sep='\t', index_label='cluster_id',
                        columns=['label'])
