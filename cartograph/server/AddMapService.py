import codecs
import csv
import json
import os
import pipes
from ConfigParser import SafeConfigParser
import falcon
import pandas
from cartograph.Utils import build_map
from cartograph.server.MapService import MapService

BASE_LANGUAGE = 'simple'
USER_CONF_DIR = 'data/conf/user/'
BASE_PATH = './data/ext/'


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
        write_file.write(read_file.readline())  # Transfer the header
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
    :param articles: file object of user data; must be TSV w/ headers on first row; 1st column must be article titles
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
        if filename == 'ids.tsv':
            external_ids = pandas.read_csv(os.path.join(target_path, filename), sep='\t', index_col='id')
            user_data_with_external_ids = user_data_with_internal_ids.join(external_ids)
            user_data_with_external_ids.set_index('externalId', inplace=True)
            user_data_with_external_ids.to_csv(os.path.join(target_path, 'metric.tsv'), sep='\t')

    data_columns = list(user_data)

    return (bad_articles, data_columns)  # FIXME: Including data_columns is maybe coupling


class AddMapService:
    """A service to allow clients to build maps from already-uploaded data files (see UploadService). When POSTed to,
    this service will attempt to filter the appropriate (TSV) data files from a parent map, which is currently
    hard-coded as 'simple'. It will then create a config file and launch the build process from that config file. Once
    built, it will add the path of that config file to the active multi-config file and the list of active maps in
    self.map_services.
    """

    def __init__(self, map_services, upload_dir):
        """Initialize an AddMapService, a service to allow the client to build maps from already uploaded data files.
        When the client POSTs to this service, if there is a file in the upload directory of the matching name (i.e.
        map_name.tsv), this service will build a map with that name from that file.

        :param map_services: (dict) a reference to dictionary whose keys are map names and values are active MapServices
        :param upload_dir: (str) path to directory containing uploaded map data files
        """
        self.map_services = map_services
        self.upload_dir = upload_dir

    def on_post(self, req, resp, map_name):
        """Making a POST request to this URL will cause the server to attempt to build a map from a file in the
        upload_dir by the name of <map_name>.tsv. If no such file exists, this service will respond with a 404.

        :param map_name: name of map that client wants built. Should be name of already-uploaded file.
        """
        # Try to open map data file, raise 404 if not found in upload directory
        map_file_name = map_name + '.tsv'
        if map_file_name not in os.listdir(self.upload_dir):
            raise falcon.HTTPNotFound
        data_file = open(os.path.join(self.upload_dir, map_file_name), 'r')

        # Make sure the server is in multi-map mode
        # FIXME: This should be a better error
        assert self.map_services['_multi_map']

        target_path = os.path.join(BASE_PATH, 'user/', map_name)
        # FIXME: Change 'simple' to a map name selected by the user
        bad_articles, data_columns = gen_data(os.path.join(BASE_PATH, BASE_LANGUAGE), target_path, data_file)
        config_path = gen_config(map_name, data_columns)

        # Build from the new config file
        build_map(config_path)

        # Add urls to server that point to new map
        map_service = MapService(config_path)
        self.map_services[map_service.name] = map_service

        # Add map config path to meta-config file
        with open(self.map_services['_meta_config'], 'a') as meta_config:
            meta_config.write('\n'+config_path)

        # Clean up: delete the uploaded map data file
        os.remove(os.path.join(self.upload_dir, map_file_name))

        # Return helpful information to client
        resp.body = json.dumps({
            'map_name': map_name,
            'bad_articles': list(bad_articles),
            'data_columns': data_columns
        })
