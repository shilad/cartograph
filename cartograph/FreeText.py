import logging

import luigi
import sys

from cartograph import Config
from Utils import read_features
from cartograph import FastKnn
from cartograph.LuigiUtils import MTimeMixin, TimestampedLocalTarget
from cartograph.PreReqs import Word2VecFile, ExternalIdFile

logger = logging.getLogger("cartograph.freetext")


class FreeText:
    def __init__(self, pathVectors, idMapping=None):
        self.idMapping = idMapping

        self.articleKnn = FastKnn(pathVectors,
                                  pathVectors + '.articles.annoy',
                                  pathVectors + '.articles.annoyIds',
                                  format='mikolov')

        self.phraseKnn = FastKnn(pathVectors,
                                  pathVectors + '.phrases.annoy',
                                  pathVectors + '.phrases.annoyIds',
                                  format='mikolov')

    def rebuildIfNecessary(self):

        def extractWpId(id):
            if id.startswith('/w/'):
                parts = id.split('/')
                if len(parts) > 3:
                    id2 = parts[3]
                    if not self.idMapping:
                        return id2
                    elif id2 in self.idMapping:
                        return self.idMapping[id2]
            return None

        def extractPhrase(id):
            if id.startswith('/w/'):
                return None
            else:
                return id

        if self.articleKnn.exists():
            logger.info('loading article knn...')
            self.articleKnn.read()
        else:
            logger.info('rebuilding article knn...')
            self.articleKnn.rebuild(extractWpId)
            logger.info('found %d articles starting with %s',
                        len(self.articleKnn.ids),
                        self.articleKnn.ids[:5])
        if self.phraseKnn.exists():
            logger.info('loading phrase knn')
            self.phraseKnn.read()
        else:
            logger.info('rebuilding phrase knn...')
            self.phraseKnn.rebuild(extractPhrase)
            logger.info('found %d phrase starting with %s',
                        len(self.phraseKnn.ids),
                        self.phraseKnn.ids[:5])

    def nearestArticlesForPhrase(self, phrase, n=5):
        v = self.phraseKnn.getVector(phrase)
        if not v: return []
        return self.articleKnn.neighbors(v, n)


    def nearestPhrasesForPhrase(self, phrase, n=5):
        v = self.phraseKnn.getVector(phrase)
        if not v: return []
        return self.phraseKnn.neighbors(v, n)

    @staticmethod
    def paths(pathVectors):
        return [
            pathVectors + '.articles.annoy',
            pathVectors + '.articles.annoyIds',
            pathVectors + '.phrases.annoy',
            pathVectors + '.phrases.annoyIds',
        ]


class FreeTextTask(MTimeMixin, luigi.Task):

    def requires(self):
        return (
            ExternalIdFile(),
            Word2VecFile(),
        )

    def output(self):
        w2vPath = Config.get().get('ExternalFiles', 'w2v')
        return [TimestampedLocalTarget(p) for p in FreeText.paths(w2vPath)]

    def run(self):
        conf = Config.get()
        w2vPath = conf.get('ExternalFiles', 'w2v')
        idMapping = {}
        for id, idInfo in read_features(conf.get('ExternalFiles', 'external_ids')).items():
            idMapping[idInfo['externalId']] = id
        ft = FreeText(w2vPath, idMapping)
        ft.rebuildIfNecessary()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    ft = FreeText('data/labdata/simple/w2v.bin')
    ft.rebuildIfNecessary()
    info = read_features('./data/labdata/simple/names.tsv', './data/labdata/simple/ids.tsv')
    names = {}
    for info in info.values():
        names[info['externalId']] = info['name']

    print ft.nearestPhrasesForPhrase('dog')

    for id, score in ft.nearestArticlesForPhrase('dog'):
        print id, names.get(id), score