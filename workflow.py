import luigi
import os
import time

class MTimeMixin:
    """
        Mixin that flags a task as incomplete if any requirement
        is incomplete or has been updated more recently than this task
        This is based on http://stackoverflow.com/a/29304506, but extends
        it to support multiple input / output dependencies.
    """

    def complete(self):
        def to_list(obj):
            if type(obj) in (type(()), type([])):
                return obj
            else:
                return [obj]
    
        def mtime(path):
            return time.ctime(os.path.getmtime(path))
    
        if not all(os.path.exists(out.path) for out in to_list(self.output())):
            return False
            
        self_mtime = min(mtime(out.path) for out in to_list(self.output()))
    
        # the below assumes a list of requirements, each with a list of outputs. YMMV
        for el in to_list(self.requires()):
            if not el.complete():
                return False
            for output in to_list(el.output()):
                if mtime(output.path) > self_mtime:
                    return False
    
        return True
    

class WikiBrain(luigi.ExternalTask):
    def output(self):
        return (
            luigi.LocalTarget("data/vectors.tsv"),
            luigi.LocalTarget("data/names.tsv")
        )

class RegionClustering(MTimeMixin, luigi.Task):
    def output(self):
        return luigi.LocalTarget("data/cluster_labels.tsv")

    def requires(self):
        return WikiBrain()

    def run(self):
        f = open('data/cluster_labels.tsv', 'w')
        f.write('writing DATA\n')
        f.close()

class Embedding(MTimeMixin, luigi.Task):
    def output(self):
        return luigi.LocalTarget("data/2d_embedding.tsv")

    def requires(self):
        return WikiBrain()

    def run(self):
        f = open('data/2d_embedding.tsv', 'w')
        f.write('writing DATA\n')
        f.close()

class DenoiseAndAddWater(MTimeMixin, luigi.Task):
    def output(self):
        return (
            luigi.LocalTarget("data/coords_and_clusters.tsv"),
            luigi.LocalTarget("data/names_and_clusters.tsv")
        )

    def requires(self):
        return RegionClustering(), Embedding()

    def run(self):
        for fn in ("data/coords_and_clusters.tsv",
                  "data/names_and_clusters.tsv"):
            f = open(fn, 'w')
            f.write('writing DATA\n')
            f.close()

