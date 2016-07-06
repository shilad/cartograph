#!/usr/bin/python
#
# export PATH=/Applications/Postgres.app/Contents/Versions/latest/bin/:$PATH
# pip2.7 install psycopg2

import logging

import os.path
import json

import psycopg2

import shapely
import shapely.wkt
import shapely.geometry 

from luigi.postgres import CopyToTable, PostgresTarget

logger = logging.getLogger('luigi-interface')


class TimestampedPostgresTarget(PostgresTarget):
    def last_mtime(self):
        with self.connect() as cnx:
            cursor = cnx.cursor()
            cursor.execute("""
                SELECT max(update_id::integer) FROM %s
                WHERE target_table = %%s""" % self.marker_table,
                (self.table, ))
            row = cursor.fetchone()
            if not row:
                return -1
            else:
                return int(row[0])

    def complete(self):
        def to_list(obj):
            if type(obj) in (type(()), type([])):
                return obj
            else:
                return [obj]

        if not self.exists(): 
            return False

        self_mtime = self.last_mtime()

        for el in to_list(self.requires()):
            if not el.complete():
                return False
            for output in to_list(el.output()):
                if mtime(output.path) > self_mtime:
                    return False
        return True



class LoadGeoJsonTask(CopyToTable):
    def __init__(self, config, table, geoJsonFilename):
        self._host = config.get('PG', 'host')
        self._database = config.get('PG', 'database')
        self._user = config.get('PG', 'user') or None
        self._password = config.get('PG', 'password') or None
        self._table = table
        self.geoJsonFilename = geoJsonFilename
        logger.info('loading %s.%s from %s' % (self._database, self._table, self.geoJsonFilename))
        super(LoadGeoJsonTask, self).__init__()

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
    def update_id(self): return str(int(os.path.getmtime(self.geoJsonFilename)))

    def run(self):
        # Part 1: Read in GeoJson and calculate property names and types
        with open(self.geoJsonFilename, 'r') as f:
            self.js = json.load(f)

        # Calculate the feature types
        self.featureTypes = self.calculateFeatureTypes()
        self.columns = ['geom'] + sorted(self.featureTypes.keys())

        CopyToTable.run(self)

    def map_column(self, value):
        mapped = CopyToTable.map_column(self, value)
        return mapped

    def calculateFeatureTypes(self):
        featureTypes = {}
        for geomJS in self.js['features']:
            for (k, v) in geomJS.get('properties', {}).items():
                tv = type(v)
                if k not in featureTypes:
                    featureTypes[k] = tv
                elif featureTypes[k] != tv:
                    raise Exception('Inconsistent type for %s: %s vs %s' % (k, featureTypes[k], tv))
        return featureTypes
 
    def init_copy(self, conn):
        # Initialize postgis if necessary
        cur = conn.cursor()
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis;')
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis_topology;')
        conn.commit()

         # Construct the schema and create the table
        assert(len(self.columns) > 0)
        schema = [ 'id serial PRIMARY KEY' ]
        for k in self.columns:
            sqlType = None
            if k == 'geom':
                sqlType = 'GEOMETRY'
            elif self.featureTypes[k] == int:
                sqlType = 'INTEGER'
            elif self.featureTypes[k] == float:
                sqlType = 'NUMERIC'
            elif self.featureTypes[k] == bool:
                sqlType = 'BOOL'
            elif self.featureTypes[k] == str:
                sqlType = 'VARCHAR'
            elif self.featureTypes[k] == unicode:
                sqlType = 'TEXT'
            else:
                raise Exception('Unknown sql type: %s' % self.featureTypes[k])
            schema.append('%s %s' % (k.lower(), sqlType))
        createSql = 'CREATE TABLE %s (%s);' % (self.table, ', '.join(schema),)
        cur.execute("DROP TABLE IF EXISTS %s;" % (self.table,))
        cur.execute(createSql)
        conn.commit()

    def rows(self):
        for geomJS in self.js['features']:
            geom = shapely.geometry.shape(geomJS['geometry'])
            row = []
            for c in self.columns:
                if c == 'geom':
                    row.append(shapely.wkt.dumps(geom))
                else:
                    row.append(geomJS.get('properties', {}).get(c))
            yield tuple(row)
        
    def post_copy(self, conn):
        cur = conn.cursor()
        # Create indexes on all fields
        for c in self.columns:
            if c == 'geom':
                indexType = 'GIST'
            elif self.featureTypes[c] in (float, int):
                indexType = 'BTREE'
            else:
                indexType = 'HASH'
            sql = ('CREATE INDEX %s_%s_idx on %s USING %s(%s)'
                    % (self.table, c, self.table, indexType, c.lower()))
            logger.info(sql)
            cur.execute(sql)
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

