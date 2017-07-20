import codecs
import csv
import json
import os
import pipes
import string
from ConfigParser import SafeConfigParser

import falcon
import pandas

from cartograph.Utils import read_vectors, build_map, read_tsv
from cartograph.server.MapService import MapService

USER_CONF_DIR = 'data/conf/user/'
BASE_PATH = './data/ext/'
ACCEPTABLE_MAP_NAME_CHARS = string.uppercase + string.lowercase + '_' + string.digits


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
    :param source_dir:
    :param target_dir:
    :param ids: an iterable of the ids (each of which should be an int)
    :param filename: the name of the file in <source_dir> to be filtered into a file of the same name in <target_dir>
    :return:
    """
    with codecs.open(os.path.join(source_dir, filename), 'r') as read_file, \
            codecs.open(os.path.join(target_dir, filename), 'w') as write_file:
        reader = csv.reader(read_file, delimiter='\t')
        writer = csv.writer(write_file, delimiter='\t', lineterminator='\n')
        writer.writerow(reader.next())  # Transfer the header
        for row in reader:
            if int(row[0]) in ids:
                writer.writerow(row)


def gen_config(map_name, column_headers):
    """Generate the config file for a user-generated map named <map_name> and return a path to it

    :param map_name: name of new map
    :param column_headers: list of headers for non-index columns
    :return: path to the newly-generated config file
    """

    if not os.path.exists(USER_CONF_DIR):
        os.makedirs(USER_CONF_DIR)

    # Generate a new config file
    # Start with base values from template
    config = SafeConfigParser()
    config.read('data/conf/BASE.txt')

    # Set name of dataset
    config.set('DEFAULT', 'dataset', map_name)

    # Record list of column names in JSON format
    config.set('DEFAULT', 'columns', json.dumps(column_headers))

    # Write newly-generated config to file
    config_filename = '%s.txt' % pipes.quote(map_name)
    config_path = os.path.join(USER_CONF_DIR, config_filename)
    config.write(open(config_path, 'w'))
    return config_path


def gen_data(source_dir, target_path, articles):
    """Generate the data files (i.e. "TSV" files) for a map with a string of articles <articles>
    in the directory at target_path.

    :param target_path: path to directory (that will be created) to be filled with data files
    :param articles: file object of user data
    :return: list of article titles for which there was no exact match in the existing dataset
    """

    # Generate dataframe of user data
    user_data = pandas.read_csv(articles, delimiter='\t')
    first_column = list(user_data)[0]
    user_data.set_index(first_column, inplace=True)  # Assume first column contains titles of articles

    # Generate dataframe of names to IDs
    names_file_path = os.path.join(source_dir, 'names.tsv')
    names_to_ids = pandas.read_csv(names_file_path, delimiter='\t', index_col='name')

    # Append internal ids with the user data; set the index to 'id';
    # preserve old index (i.e. 1st column goes to 2nd column)
    user_data_with_internal_ids = user_data.join(names_to_ids)
    user_data_with_internal_ids[first_column] = user_data_with_internal_ids.index
    user_data_with_internal_ids.set_index('id', inplace=True)

    # Generate list of IDs for article names in user request
    ids = set(user_data_with_internal_ids.index)
    bad_articles = set()

    # Create the destination directory (if it doesn't exist already)
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # For each of the primary data files, filter it and output it to the target directory
    for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv']:
        filter_tsv(source_dir, target_path, ids, filename)

    data_columns = list(user_data)

    return (bad_articles, data_columns)  # FIXME: Including data_columns is maybe coupling



def check_map_name(map_name, map_services):
    """Check that map_name is not already in map_services, that all of its characters are in
    the list of acceptable characters, and that there is no existing directory named map_name in
    data/ext/user (i.e. the place where data for user maps is stored). If any of these conditions
    is not met, this will raise a ValueError with an appropriate message.

    :param map_name: Name of the map to check
    :param map_services: (pointer to) dictionary whose keys are names of currently active maps
    """
    # FIXME: This does not check if a non-user-generated non-active map with the same name \
    # FIXME: already exists. I can't think of an easy way to fix that.

    # Prevent map names with special characters (for security/prevents shell injection)
    bad_chars = set()
    for c in map_name:
        if c not in ACCEPTABLE_MAP_NAME_CHARS:
            bad_chars.add(c)
    if bad_chars:
        bad_char_string = ', '.join(['"%s"' % (c,) for c in bad_chars])
        good_char_string = ', '.join(['"%s"' % (c,) for c in ACCEPTABLE_MAP_NAME_CHARS])
        raise ValueError('Map name "%s" contains unacceptable characters: [%s]\n'
                         'Accepted characters are: [%s]' % (map_name, bad_char_string, good_char_string))

    # Prevent adding a map with the same name as a currently-served map
    # This will prevent adding user-generated maps with the same names as
    # active non-user-generated maps, e.g. "simple" or "en"
    if map_name in map_services.keys():
        raise ValueError('Map name "%s" already in use for an active map!' % (map_name,))

    # Prevent adding a map for which there is already a user-generated map
    # of the same name
    if map_name in os.listdir(os.path.join(BASE_PATH, 'user')):
        raise ValueError('Map name "%s" already taken by a user-generated map' % (map_name,))


class AddMapService:
    """A service to allow clients to build maps from already-uploaded data files. When POSTed to, this service will
    attempt to filter the appropriate (TSV) data files from a parent map, which is currently hard-coded as 'simple'.
    It will then create a config file and launch the build process from that config file. Once built, it will add the
    path of that config file to the active multi-config file and the list of active maps in self.map_services.
    """

    def __init__(self, map_services, upload_dir):
        """Initialize an AddMapService, a service to allow the client to build maps from already uploaded data files.
        :param map_services:
        :param upload_dir:
        """
        self.map_services = map_services
        self.upload_dir = upload_dir

    def on_get(self, req, resp, map_name):
        map_file_name = map_name + '.tsv'
        if map_file_name not in os.listdir(self.upload_dir):
            raise falcon.HTTPNotFound

        resp.stream = open('templates/add_map.html', 'rb')
        resp.content_type = 'text/html'

    def on_post(self, req, resp, map_name):
        # 404 if map data file not in the upload directory
        map_file_name = map_name + '.tsv'
        if map_file_name not in os.listdir(self.upload_dir):
            raise falcon.HTTPNotFound

        # Make sure the server is in multi-map mode
        # FIXME: This should be a better error
        assert self.map_services['_multi_map']

        data_file = open(os.path.join(self.upload_dir, map_file_name), 'r')


        # TODO: Move this to UploadService
        check_map_name(map_name, self.map_services)

        target_path = os.path.join(BASE_PATH, 'user/', map_name)
        # TODO: Figure out what to do with <bad_articles>
        # FIXME: Change 'simple' to a map name selected by the user
        bad_articles, data_columns = gen_data(os.path.join(BASE_PATH, 'simple'), target_path, data_file)
        config_path = gen_config(map_name, data_columns)

        # Build from the new config file
        build_map(config_path)

        # Add urls to new map
        map_service = MapService(config_path)
        self.map_services[map_service.name] = map_service

        # Add map config path to meta-config
        with open(self.map_services['_meta_config'], 'a') as meta_config:
            meta_config.write('\n'+config_path)

        resp.body = json.dumps({
            'map_name': map_name,
            'bad_articles': list(bad_articles),
            'data_columns': data_columns
        })
