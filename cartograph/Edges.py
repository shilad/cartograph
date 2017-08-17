import luigi
import logging

from luigi import postgres
from luigi.postgres import CopyToTable

logger = logging.getLogger('cartograph.edges')

from cartograph import MapConfig
from cartograph.Coordinates import CreateFullCoordinates
from cartograph.LuigiUtils import TimestampedLocalTarget, MTimeMixin, TimestampedPostgresTarget, to_list
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

class LoadCoordinateEdges(MTimeMixin, postgres.CopyToTable):
    def __init__(self):
        config = MapConfig.get()
        self._host = config.get('PG', 'host')
        self._database = config.get('PG', 'database')
        self._user = config.get('PG', 'user') or None
        self._password = config.get('PG', 'password') or None
        self._table = 'edges'
        self._dataFile = config.get('GeneratedFiles', 'edge_bundles')
        self.columns = ['bundle', 'weights', 'numPoints', 'endPoints']
        logger.info('loading %s.%s from %s' % (self._database, self._table, self._dataFile))
        super(LoadCoordinateEdges, self).__init__()

        print self.table

    @property
    def host(self): return self._host
    @property
    def database(self): return self._database
    @property
    def user(self): return self._user
    @property
    def password(self): return self._password
    @property
    def table(self): return self._table
    @property
    def update_id(self):
        max_mtime = -1
        for el in to_list(self.requires()):
            if not el.complete():
                return self.table + '_100000000000000000000000000'
            for output in to_list(el.output()):
                max_mtime = max(output.mtime(), max_mtime)
        return self.table + '_' + str(max_mtime)

    def requires(self):
        return _CreateEdgeBundles(), _CreateEdgesCode()

    def init_copy(self, conn):
        cnx = self.output().connect()
        cur = cnx.cursor()
        cur.execute("DROP TABLE IF EXISTS edges;")
        sql = """
        CREATE TABLE edges (
          id serial PRIMARY KEY,
          bundle GEOMETRY,
          weights TEXT,
          numPoints INTEGER,
          endPoints GEOMETRY
        );
        """
        cur.execute(sql)
        cnx.commit()

    def rows(self):
        with open(self._dataFile) as f:
            for i, line in enumerate(f):
                parts = line.rstrip('\n').split('\t')
                assert(len(parts) == 4)
                parts[2] = int(parts[2])
                if parts[2] > 2:
                    yield tuple(parts)

    def post_copy(self, conn):
        cur = conn.cursor()
        cur.execute('CREATE INDEX edges_num_points_idx ON edges USING BTREE(numPoints)')
        cur.execute('CREATE INDEX edges_endpoints_idx ON edges USING GIST(endpoints)')
        conn.commit()

    def output(self):
        """

        Returns a PostgresTarget representing the inserted dataset.
        Normally you don't override this.
        """
        return TimestampedPostgresTarget(
            host=self.host,
            database=self.database,
            user=self.user,
            password=self.password,
            table=self.table,
            update_id=self.update_id
        )
