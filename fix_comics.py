#!/usr/bin/python2.7

import pandas as pd
import numpy as np

metrics = pd.read_table('./data/comics/ext/metrics.tsv', index_col=0)

names = metrics[['name']]
names.to_csv('./data/comics/ext/names.tsv', sep='\t')

pop = metrics[['APPEARANCES']]
pop.columns = ['popularity']
pop = pop.fillna(0)
pop.to_csv('./data/comics/ext/popularity.tsv', sep='\t')


def log4(x): return np.log2(x) / np.log2(4)
zpop = metrics[[]]
zpop['zpop'] = log4(np.arange(zpop.shape[0]) / 2.0 + 1.0)

zpop.to_csv('./data/comics/gen/tsv/zpop.tsv', sep='\t')

