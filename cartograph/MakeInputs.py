#!/usr/bin/env python2.7
#
# Takes a server config, map config, and upload file and
# generates input files for that map config.
#
# Example usage:
#
# ./bin/docker-cmd.sh python
#               ./cartograph/MakeInputs.py
#               ./conf/default_server.conf
#               ./data/conf/mymap.conf
#               ./data/upload/demo_data.tsv
#
# The config file is written in AddMapService2.AddMapService.gen_config
#




import codecs
import csv
import json

import os
from ConfigParser import SafeConfigParser

import plyvel
import shutil

from IdFinder import IdFinder

import pandas


STATUS_NOT_STARTED = 'NOT_STARTED'
STATUS_RUNNING = 'RUNNING'
STATUS_FAILED = 'FAILED'
STATUS_SUCCEEDED = 'SUCCEEDED'

def warn(message):
    sys.stderr.write(message + '\n')


def make_db(source_dir):
    names = ['categories.tsv', 'ids.tsv', 'names.tsv', 'vectors.tsv', 'links.tsv', 'popularity.tsv' ]
    paths = [ os.path.join(source_dir, n) for n in names ]
    times = [os.path.getmtime(db_path) for db_path in paths ]
    hash = int(sum(times))

    # See if there is an up to date database cache
    db_path = os.path.join(source_dir, 'concepts.db')
    if os.path.isdir(db_path):
        db = plyvel.DB(db_path)
        hash2 = db.get('__hash__')
        if hash2 and int(hash2) == hash:
            warn('Using up to date concepts db')
            return db
        warn('Data in %s is stale; Rebuilding now.' % (db_path,))
        db.close()
        shutil.rmtree(db_path)


    # Build up the relatively small portions of the data.

    concepts = {}
    required_fields = {'vector'}
    for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv']:
        warn('loading data from %s' % (filename))
        source_file_path = os.path.join(source_dir, filename)
        with open(source_file_path, 'r') as source_file:
            source = csv.reader(source_file, delimiter='\t', lineterminator='\n')
            fields = source.next()
            for i, row in enumerate(source):
                if i % 100000 == 0:
                    warn('loading line %d of %s' % (i, source_file_path))

                id = int(row[0])
                if filename == 'vectors.tsv':
                    info = { 'vector' : map(float, row[1:])}
                elif filename == 'links.tsv':
                    info = { 'links' : map(int, row[1:])}
                else:
                    info = dict(zip(fields[1:], row[1:]))
                    required_fields.update(info.keys())

                if id not in concepts: concepts[id] = { 'id' : id }
                concepts[id].update(info)

    warn('found %d concepts' % (len(concepts),))
    concepts = { id: info
                 for (id, info) in concepts.items()
                 if all(f in info for f in required_fields) }
    warn('pruned to %d concepts that had all fields (%s)'
         % (len(concepts), ', '.join(required_fields)))

    db = plyvel.DB(db_path,  create_if_missing=True)
    wb = db.write_batch()
    external_to_internal = { int(concepts[id]['externalId']) : id for id in concepts }
    cat_path = os.path.join(source_dir, 'categories.tsv')
    with open(cat_path, 'r') as source_file:
        warn('loading data from %s' % (cat_path))
        header = source_file.next() # ignore header
        for i, line in enumerate(source_file):
            if i % 10000 == 0:
                warn('loading line %d of %s' % (i, cat_path))
                wb.write()
                wb = db.write_batch()

            row = line.strip().split('\t')
            ext_id = int(row[0])
            int_id = external_to_internal.get(ext_id, -1)
            cats = row[1:]

            if int_id >= 0 and int_id in concepts:
                record = dict(concepts[int_id])
                record['cats'] = cats
                wb.put(str(int_id), json.dumps(record))

    wb.put('__hash__', str(hash))
    wb.write()
    db.close()

    db = plyvel.DB(db_path)
    return db


def main(server_config, map_config, input_path):

    source_dir = server_conf.get('DEFAULT', 'source_dir')
    db = make_db(source_dir)

    gen_data(db, server_config, map_config, input_path)

    # Read in the metric file and add layers
    layer_tsv = os.path.join(map_config.get('DEFAULT', 'externalDir'), 'metrics.tsv')
    layer_df = pandas.read_csv(layer_tsv, sep='\t')
    layer_df.path = layer_tsv

    for layer_name in map_config.get('Metrics', 'active').split():
        add_layer(map_config, layer_name, layer_df)



def gen_data(db, server_conf, map_config, input_file):
    """Generate the data files (i.e. "TSV" files) for a map with a string of articles <articles>
    in the directory at target_path.

    :param target_path: path to directory (that will be created) to be filled with data files
    :param input_file: file object of user data; must be TSV w/ headers on first row; 1st column must be article titles
    :return: tuple (set of article titles not found in source data, list of column headers excluding first column)
    """
    source_dir = server_conf.get('DEFAULT', 'source_dir')

    # Generate dataframe of user data
    user_data = pandas.read_csv(input_file, delimiter='\t')
    first_column = list(user_data)[0]
    user_data.drop_duplicates(subset=first_column, inplace=True)  # Eliminate duplicates; keep 1st instance
    user_data.set_index(first_column, inplace=True)  # Assume first column contains titles of articles
    all_articles = set(user_data.index.values)

    # Generate dictionary of names to (Source Data, Internal) IDs
    name_to_internal = {}
    names_file_path = os.path.join(source_dir, 'names.tsv')
    with open(names_file_path, 'r') as names_file:
        names_file.readline()  # Skip the header
        names = csv.reader(names_file, delimiter='\t')
        for row in names:
            name_to_internal[row[1]] = int(row[0])

    # Generate dictionary of external IDs to source internal IDs
    external_to_internal = {}  # FIXME: Rename to external_ids?
    ids_file_path = os.path.join(source_dir, 'ids.tsv')
    with open(ids_file_path, 'r') as ids_file:
        ids_file.readline()  # Skip the header
        ids = csv.reader(ids_file, delimiter='\t')
        for row in ids:
            external_to_internal[int(row[1])] = int(row[0])

    # Make ID Finder from dictionaries and use it to find matches for articles
    id_finder = IdFinder(name_to_internal, external_to_internal, 'en')  # FIXME: Language code should be dynamic
    all_matches, bad_articles = id_finder.get_all_matches(all_articles)

    # Assign a new internal ID to each article match
    new_ids = {}  # Dictionary mapping titles (as in user data) to new internal IDs
    new_names = {} # Dictionary mapping new internal IDs to titles (as in user data)
    old_to_new = {}  # Dictionary mapping old IDs to sets of new IDs
    new_to_old = {}
    id_counter = 1
    for title in all_matches:
        old_id = all_matches[title]
        if old_id in old_to_new:
            old_to_new[old_id].add(id_counter)
        else:
            old_to_new[old_id] = {id_counter}
        new_to_old[id_counter] = old_id
        new_ids[title] = id_counter
        new_names[id_counter] = title
        id_counter += 1

    # Create the destination directory (if it doesn't exist already)
    target_path = map_config.get('DEFAULT', 'externalDir')
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # For each of the primary data files, filter it and output it to the target
    # directory  # FIXME: This comment is not totally accurate
    external_ids = {}  # Dictionary of (new) internal IDs to external IDs
    for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv', 'categories.tsv']:
        source_file_path = os.path.join(source_dir, filename)
        target_file_path = os.path.join(target_path, filename)
        with open(source_file_path, 'r') as source_file:
            with open(target_file_path, 'w') as target_file:
                source = csv.reader(source_file, delimiter='\t', lineterminator='\n')
                target = csv.writer(target_file, delimiter='\t', lineterminator='\n')
                if filename == 'categories.tsv':
                    fields = None
                else:
                    fields = source.next()
                    target.writerow(fields)

                for new_id in new_to_old:
                    old_id = new_to_old[new_id]
                    record_str = db.get(str(old_id))

                    if not record_str: continue

                    record = json.loads(record_str)
                    external_id = record['externalId']


                    if filename == 'categories.tsv':
                        row = [new_id] + [c + ':1' for c in record.get('cats', [])]
                    elif filename == 'vectors.tsv':
                        row =  [new_id] + record['vector']
                    else:
                        assert(len(fields) == 2)
                        row = [new_id, record[fields[1]]]

                    row = map(lambda s: unicode(s).encode('utf-8'), row)

                    target.writerow(row)

                    external_ids[new_id] = external_id


    # Save user-provided data as metrics.tsv
    # FIXME: There should be some named constants in here
    data_columns = list(user_data)
    with open(os.path.join(target_path, 'metrics.tsv'), 'w') as metric_file:
        metric_writer = csv.writer(metric_file, delimiter='\t', lineterminator='\n')
        metric_writer.writerow(['id', 'externalId', first_column] + data_columns)
        for title, row in user_data.iterrows():
            if title in new_ids:
                internal_id = new_ids[title]
                if internal_id in external_ids:
                    external_id = external_ids[internal_id]
                    new_row = [internal_id, external_id, title] + [row[column] for column in data_columns]
                    metric_writer.writerow(new_row)

    return (bad_articles, data_columns)  # FIXME: Including data_columns is maybe coupling


def add_layer(map_config, layer_name, metric_df):
    """
    Adds a single layer to the config.
    metric_df is the data frame associated with all metrics. We presume it has a "path" attribute

      {
         "field":"Popularity",
         "id":"pop",
         "title":"Popularity",
         "description":"Popularity",
         "datatype":"sequential",
         "numColors":"3"
      }
    """

    info = json.loads(map_config.get('Metrics', layer_name))

    field = info['field']

    # Load user data to mine for appropriate values
    metric_type = info['datatype']

    # Configure settings for a metric
    metric_settings = {
        'datatype': metric_type,
        'field': field,
        'description' : info['description'],
        'title' : info['title'],
        'colorscheme': info['colorscheme']
    }

    # Add more info to metric settings depending on type
    if metric_type == 'diverging':
        metric_settings.update({
            'maxVal': metric_df[field].max(),
            'minVal': metric_df[field].min()
        })
    elif layer_name == 'cluster':
        numClusters = int(info['colorscheme'].split('_')[-1]) # Gets "7" from "Accent_7"
        metric_settings['scale'] = list(str(i) for i in range(numClusters))
    elif metric_type == 'qualitative':
        metric_settings['scale'] = sorted(list(metric_df[field].unique()))
    elif metric_type == 'sequential':
        metric_settings['maxValue'] = metric_df[field].max()
    else:
        raise Exception("Unknown datatype: " + metric_type)

    c = SafeConfigParser()
    c.read(map_config.path)

    # Define new metric in config file
    c.set('Metrics', layer_name, json.dumps(metric_settings))

    active = []
    if c.has_option('Metrics', 'active'):
        active = c.get('Metrics', 'active').split()
    if layer_name not in active:
        c.set('Metrics', 'active', ' '.join(active + [layer_name]))

    with open(map_config.path, 'w') as f:
        c.write(f)

if __name__ == '__main__':
    import sys

    from cartograph import MapConfig
    from cartograph.server import ServerConfig

    if len(sys.argv) != 4:
        sys.stderr.write('Usage: path_server_conf path_map_conf path_input\n')
        sys.exit(1)

    server_conf = ServerConfig.create(sys.argv[1])
    map_conf = MapConfig.createConf(sys.argv[2])

    main(server_conf, map_conf, sys.argv[3])
