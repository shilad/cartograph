import luigi

class WikiBrain(luigi.ExternalTask):
    version = luigi.IntParameter()

    def output(self):
        return (
            luigi.LocalTarget("data/vectors.tsv.%d" % self.version),
            luigi.LocalTarget("data/names.tsv.%d" % self.version)
        )

class RegionClustering(luigi.Task):
    version = luigi.IntParameter()

    def output(self):
        return luigi.LocalTarget("data/cluster_labels.tsv.%d" % self.version)

    def requires(self):
        return WikiBrain(self.version)

    def run(self):
        f = open('data/cluster_labels.tsv.%d' % self.version, 'w')
        f.write('writing version %s\n' % self.version)
        f.close()

class Embedding(luigi.Task):
    version = luigi.IntParameter()

    def output(self):
        return luigi.LocalTarget("data/2d_embedding.tsv.%d" % self.version)

    def requires(self):
        return WikiBrain(self.version)

    def run(self):
        f = open('data/2d_embedding.tsv.%d' % self.version, 'w')
        f.write('writing embedding version %s\n' % self.version)
        f.close()

class DenoiseAndAddWater(luigi.Task):
    version = luigi.IntParameter()

    def output(self):
        return (
            luigi.LocalTarget("data/coords_and_clusters.tsv.%d" % self.version),
            luigi.LocalTarget("data/names_and_clusters.tsv.%d" % self.version)
        )

    def requires(self):
        return RegionClustering(self.version), Embedding(self.version)

    def run(self):
        for fn in ("data/coords_and_clusters.tsv.%d" % self.version,
                  "data/names_and_clusters.tsv.%d" % self.version):
            f = open(fn, 'w')
            f.write('writing %s, version %s\n' % (fn, self.version))
            f.close()

