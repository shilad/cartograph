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
from IdFinder import IdFinder

import pandas


STATUS_NOT_STARTED = 'NOT_STARTED'
STATUS_RUNNING = 'RUNNING'
STATUS_FAILED = 'FAILED'
STATUS_SUCCEEDED = 'SUCCEEDED'


def main(server_config, map_config, input_path):

    gen_data(server_config, map_config, input_path)

    # Read in the metric file and add layers
    layer_tsv = os.path.join(map_config.get('DEFAULT', 'externalDir'), 'metrics.tsv')
    layer_df = pandas.read_csv(layer_tsv, sep='\t')
    layer_df.path = layer_tsv

    for layer_name in map_config.get('Metrics', 'active').split():
        add_layer(map_config, layer_name, layer_df)

def gen_data(server_conf, map_config, input_file):
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
    names_dict = {}
    names_file_path = os.path.join(source_dir, 'names.tsv')
    with open(names_file_path, 'r') as names_file:
        names_file.readline()  # Skip the header
        names = csv.reader(names_file, delimiter='\t')
        for row in names:
            names_dict[row[1]] = int(row[0])

    # Generate dictionary of external IDs to source internal IDs
    ids_dict = {}  # FIXME: Rename to external_ids?
    ids_file_path = os.path.join(source_dir, 'ids.tsv')
    with open(ids_file_path, 'r') as ids_file:
        ids_file.readline()  # Skip the header
        ids = csv.reader(ids_file, delimiter='\t')
        for row in ids:
            ids_dict[int(row[1])] = int(row[0])

    # Make ID Finder from dictionaries and use it to find matches for articles
    id_finder = IdFinder(names_dict, ids_dict, 'simple')  # FIXME: Language code should be dynamic
    all_matches, bad_articles = id_finder.get_all_matches(all_articles)

    # Assign a new internal ID to each article match
    new_ids = {}  # Dictionary mapping titles (as in user data) to new internal IDs
    id_map = {}  # Dictionary mapping old IDs to sets of new IDs
    id_counter = 1
    for title in all_matches:
        old_id = all_matches[title]
        if old_id in id_map:
            id_map[old_id].add(id_counter)
        else:
            id_map[old_id] = {id_counter}
        new_ids[title] = id_counter
        id_counter += 1

    # Create the destination directory (if it doesn't exist already)
    target_path = map_config.get('DEFAULT', 'externalDir')
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # For each of the primary data files, filter it and output it to the target
    # directory  # FIXME: This comment is not totally accurate
    external_ids = {}  # Dictionary of (new) internal IDs to external IDs
    for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv']:
        source_file_path = os.path.join(source_dir, filename)
        target_file_path = os.path.join(target_path, filename)
        with open(source_file_path, 'r') as source_file:
            with open(target_file_path, 'w') as target_file:
                source = csv.reader(source_file, delimiter='\t', lineterminator='\n')
                target = csv.writer(target_file, delimiter='\t', lineterminator='\n')
                target_file.write(source_file.readline())
                for row in source:
                    old_id = int(row[0])
                    if old_id in id_map:
                        for new_id in id_map[old_id]:
                            new_row = [new_id]+row[1:]
                            target.writerow(new_row)
                            if filename == 'ids.tsv':
                                external_ids[new_id] = int(row[1])
    
    # Save user-provided data as metrics.tsv
    # FIXME: There should be some named constants in here
    data_columns = list(user_data)
    with open(os.path.join(target_path, 'metrics.tsv'), 'w') as metric_file:
        metric_writer = csv.writer(metric_file, delimiter='\t', lineterminator='\n')
        metric_writer.writerow(['externalId', first_column] + data_columns)
        for title, row in user_data.iterrows():
            if title in new_ids:
                external_id = external_ids[new_ids[title]]
                new_row = [external_id, title] + [row[column] for column in data_columns]
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
        'path': metric_df.path,
        'field': field,
        'colorscheme': info['colorscheme']
    }

    # Add more info to metric settings depending on type
    if metric_type == 'diverging':
        metric_settings.update({
            'maxVal': metric_df[field].max(),
            'minVal': metric_df[field].min()
        })
    elif metric_type == 'qualitative':
        metric_settings.update({
            'scale': list(metric_df[field].unique())
        })
    elif metric_type == 'sequential':
        metric_settings.update({
            'maxValue': metric_df[field].max()
        })
    else:
        raise Exception("Unknown datatype: " + metric_type)

    c = SafeConfigParser()
    c.read(map_config.path)

    # Define new metric in config file
    c.set('Metrics', layer_name, json.dumps(metric_settings))

    active = []
    if c.has_option('Metrics', 'active'):
        active = c.get('Metrics', 'active').split()
    c.set('Metrics', 'active', ' '.join(active + [id]))

    with open(map_config.path, 'w') as f:
        c.write(f)

def filter_tsv(source_dir, target_dir, ids, filename):
    """Pare down the contents of <source_dir>/<filename> to only rows that start with an id in <ids>, and output them to
    <target_dir>/<filename>. <target_dir> must already exist. Also transfers over the first line of the file, which is
    assumed to be the header.
    e.g.
    filter_tsv(source_dir='/some/path/', dest_dir='/another/path', ids=['1', '3', '5'], filename='file.tsv')
    /some/path/file.tsv (before function call):
    id  name
    1   hello
    2   world
    3   foo
    4   bar
    5   spam
    /another/path/file.tsv (after function call):
    id  name
    1   hello
    3   foo
    5   spam
    :param source_dir: str of path to dir containing source data files (i.e. "/some/path/")
    :param target_dir: str of path to dir where result data files will be placed (i.e. "/another/path/")
    :param ids: an iterable of ids (each member should be a str); result data files will only have rows w\ these ids
    :param filename: the name of the file in <source_dir> to be filtered into a file of the same name in <target_dir>
    :return:
    """
    with codecs.open(os.path.join(source_dir, filename), 'r') as read_file, \
            codecs.open(os.path.join(target_dir, filename), 'w') as write_file:
        reader = csv.reader(read_file, delimiter='\t')
        writer = csv.writer(write_file, delimiter='\t', lineterminator='\n')
        write_file.write(read_file.readline())  # Transfer the header
        for row in reader:
            if row[0] in ids:
                writer.writerow(row)


def get_status_path(server_conf, map_id):
    return server_conf.getForDataset(map_id, 'DEFAULT', 'ext_dir') + '/status.txt'


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
