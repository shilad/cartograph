import luigi
import logging

logger = logging.getLogger('cartograph.edges')

from cartograph import MapConfig
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import TimestampedLocalTarget, MTimeMixin, to_list
from cartograph.Utils import read_features

class _CreateEdgesCode(MTimeMixin, luigi.ExternalTask):
    def output(self):
        return(TimestampedLocalTarget(__file__))


class _RawEdges(MTimeMixin, luigi.ExternalTask):

    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("ExternalFiles", "links"))

    def requires(self):
        return []

class CreateCoordinateEdges(MTimeMixin, luigi.Task):

    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "edges_with_coords"))


    def requires(self):
        return (
            _CreateEdgesCode(),
            CreateFullCoordinates(),
            _RawEdges()
        )

    def run(self):
        config = MapConfig.get()
        coords = read_features(config.get("GeneratedFiles", "article_coordinates"))
        pathIn = config.get("ExternalFiles", "links")
        pathOut = config.get("GeneratedFiles", "edges_with_coords")
        with open(pathIn) as fin, open(pathOut, 'w') as fout:

            logging.getLogger('counting edges')
            # Count num of valid edges and vertices
            numEdges = 0
            numVertices = 0
            for line in fin:
                vertices = line.split()
                src = vertices[0]
                if src not in coords: continue
                numVertices += 1
                for dest in vertices[1:]:
                    if dest in coords: numEdges += 1
            logger.info('found %d edges containing %d vertices (out of %d total vertices)'
                        % (numEdges, numVertices, len(coords)))

            fin.seek(0)
            fout.write(str(numEdges) + '\n')
            for line in fin:
                vertices = line.split()
                src = vertices[0]
                if src not in coords: continue
                numVertices += 1
                for dest in vertices[1:]:
                    if dest in coords:
                        fields = (coords[src]['x'], coords[src]['y'], coords[dest]['x'], coords[dest]['y'])
                        fout.write(' '.join(fields) + '\n')

            fin.close()
            fout.close()

class _CreateEdgeBundles(MTimeMixin, luigi.Task):
    def output(self):
        config = MapConfig.get()
        return TimestampedLocalTarget(config.get("GeneratedFiles", "edge_bundles"))


    def requires(self):
        return (
            # _CreateEdgesCode(),
            # CreateCoordinateEdges()
        )

    def run(self):
        config = MapConfig.get()
        assert(False)
