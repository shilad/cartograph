import sys

import bz2

from cartograph import Config
from cartograph import read_features


def main(conf, pathIn):
    external2Internal = {}
    for id, record in read_features(conf.get('ExternalFiles', 'external_ids')).items():
        external2Internal[record['externalId']] = id
    qualities = {}
    if pathIn.lower().endswith('bz2'):
        f = bz2.BZ2File(pathIn, 'r')
    else:
        f = open(pathIn, 'r')
    for i, line in enumerate(f):
        if i % 500000 == 0:
            print 'processing line %d, found %d' % (i, len(qualities))
        if i == 0: continue     # skip header
        tokens = line.split('\t')
        externalId = tokens[0]
        grade = tokens[4]
        score = float(tokens[5])
        print externalId, grade, score
        if externalId in external2Internal:
            qualities[externalId] = grade, score

main(Config.initConf(sys.argv[1]), sys.argv[2])