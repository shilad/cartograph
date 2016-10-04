import sys

from cartograph import Config
from cartograph import read_features
from cartograph.Utils import write_tsv

conf = Config.initConf(sys.argv[1])

feats = read_features(conf.get('DEFAULT', 'metricDir') + '/quality.tsv')
externalIds = read_features(conf.get('ExternalFiles', 'external_ids'))

ids = []
grades = []
scores = []

for id, info in feats.items():
    ids.append(externalIds[id]['externalId'])
    grades.append(info['grade'])
    scores.append(info['score'])

write_tsv(conf.get('DEFAULT', 'metricDir') + '/quality.tsv',
          ['id', 'grade', 'score'],
          ids, grades, scores)