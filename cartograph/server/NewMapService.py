import StringIO
from ConfigParser import SafeConfigParser
import json
import falcon
import os
import subprocess
import string
import pipes
import pandas

from cartograph.Utils import read_vectors
from cartograph.server.MapService import MapService

USER_CONF_DIR = 'data/conf/user/'
BASE_PATH = './data/ext/'
SOURCE_DIR = os.path.join(BASE_PATH, 'simple/')  # Path to source data (which will be pared down for the user)
ACCEPTABLE_MAP_NAME_CHARS = string.uppercase + string.lowercase + '_' + string.digits


def gen_config(map_name, metric_type, fields):
    """Generate the config file for a user-generated map named <map_name> and return a path to it

    :param map_name: name of new map
    :param metric_type: type of metric as a string, e.g. 'BIVARIATE' or 'COUNT'
    :param fields: a list of the fields that are used for the metric
    :return: path to the newly-generated config file
    """
    TYPE_NAME = {'BIVARIATE': 'bivariate-scale', 'COUNT': 'count', 'NONE': None}

    if not os.path.exists(USER_CONF_DIR):
        os.makedirs(USER_CONF_DIR)

    # Generate a new config file
    # Start with base values from template
    config = SafeConfigParser()
    config.read('data/conf/BASE.txt')

    # Set name of dataset
    config.set('DEFAULT', 'dataset', map_name)

    if metric_type != 'NONE':
        # Configure settings for one metric
        metric_settings = {
            'type': TYPE_NAME[metric_type],
            'path': '%(externalDir)s/metric.tsv',
            'fields': fields,
            'colors': ['#f11', '#1d1'],
            'percentile': True,
            'neutralColor': '#bbb',
            'maxValue': 1.0
        }
        # WARNING: this config format normalizes to all-lowercase in some places but is case-sensitive in others. Beware!
        metric_name = string.lower(fields[0])  # TODO: figure out how to name metrics other than with the first field; also figure out how to do count
        config.set('Metrics', 'active', metric_name)
        config.set('Metrics', metric_name, json.dumps(metric_settings))

    config_filename = '%s.txt' % pipes.quote(map_name)
    config_path = os.path.join(USER_CONF_DIR, config_filename)
    config.write(open(config_path, 'w'))
    return config_path


def gen_data(target_path, articles):
    """Generate the data files (i.e. "TSV" files) for a map with a string of articles <articles>
    in the directory at target_path.

    :param target_path: path to directory (that will be created) to be filled with data files
    :param articles: list of exact titles of articles for new map
    :return: list of article titles for which there was no exact match in the existing dataset
    """

    # Generate dataframe of user data
    user_data = pandas.read_csv(articles, delimiter='\t')
    first_column = list(user_data)[0]
    user_data.set_index(first_column, inplace=True)  # Assume first column contains titles of articles

    # Generate dataframe of names to IDs
    names_file_path = os.path.join(SOURCE_DIR, 'names.tsv')
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

        # Read the file into a dataframe (source_data)
        source_file_path = os.path.join(SOURCE_DIR, filename)
        if filename == 'vectors.tsv':
            # There's a special function for reading vectors.tsv, but it leaves the index as a Series of str's,
            # which is inconsistent with the members of the <ids> set (each of which is an int).
            source_data = read_vectors(source_file_path)
            source_data.index = source_data.index.map(int)
        else:
            source_data = pandas.read_csv(source_file_path, sep='\t', index_col='id')

        # Filter the dataframe
        filtered_data = source_data[source_data.index.isin(ids)]

        # Use ids.tsv for replacing internal ids with external ids, then write the output to file
        # FIXME: What happens when there's no match for an article? This needs to be determined upstream
        if filename == 'ids.tsv':
            # Make a new dataframe, replacing [internal] id with corresponding external id
            user_data_with_external_ids = user_data_with_internal_ids.join(filtered_data)
            user_data_with_external_ids.set_index('externalId', inplace=True)

            # Write to file
            metric_file_path = os.path.join(target_path, 'metric.tsv')
            user_data_with_external_ids.to_csv(metric_file_path, sep='\t')


        # Write the dataframe to the target file
        target_file_path = os.path.join(target_path, filename)
        if filename == 'vectors.tsv':
            # Treat vectors.tsv as a special case because it is *not* a true TSV (for some reason)
            write_vectors(filtered_data, target_file_path)
        else:
            # For all other TSVs, just write them normally
            filtered_data.to_csv(target_file_path, sep='\t')

    return bad_articles


def write_vectors(filtered_data, target_file_path):
    """Special function to write a vectors file, because vectors.tsv is *not* a true TSV >:(
    """
    filtered_data.index.name = 'id'  # FIXME: w/o this line, it comes out as 'index' (just in vectors.tsv)
    with open(target_file_path, 'w') as target_file:
        # Write the header
        target_file.write('\t'.join([filtered_data.index.name] + list(filtered_data)) + '\n')
        for index, row in filtered_data.iterrows():
            # str of the vector, each component separated by tabs
            # FIXME: components should be in scientific notation
            vector = '\t'.join([str(component) for component in row[0]])
            target_file.write(str(index) + '\t' + vector + '\n')


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

    def __init__(self, map_services):
        self.map_services = map_services

    def on_get(self, req, resp):
        resp.stream = open('./web/newMap.html', 'rb')
        resp.content_type = 'text/html'

    def on_post(self, req, resp):
        # Make sure the server is in multi-map mode
        # FIXME: This should be a better error
        assert self.map_services['_multi_map']

        post_data = falcon.uri.parse_query_string(req.stream.read())
        resp.body = ''

        map_name = post_data['name']
        metric = post_data['metric']
        fields = [] if metric == 'NONE' else post_data['fields'].split(':')
        # FIXME: non-ASCII compatible?
        articles_file = StringIO.StringIO(post_data['articles'])

        check_map_name(map_name, self.map_services)

        target_path = os.path.join(BASE_PATH, 'user/', map_name)
        bad_articles = gen_data(target_path, articles_file)  # TODO: Figure out what to do with <bad_articles>
        config_path = gen_config(map_name, metric, fields)

        # Build from the new config file
        python_path = os.path.expandvars('$PYTHONPATH:.:./cartograph')
        working_dir = os.getcwd()
        exec_path = os.getenv('PATH')
        subprocess.call(
            ['luigi', '--module', 'cartograph', 'ParentTask', '--local-scheduler'],
            env={'CARTOGRAPH_CONF': config_path, 'PYTHONPATH': python_path, 'PWD': working_dir, 'PATH': exec_path},
            stdout=open(os.path.join(target_path, 'build.log'), 'w'),
            stderr=open(os.path.join(target_path, 'build.err'), 'w')
        )

        # Add urls to new map
        map_service = MapService(config_path)
        self.map_services[map_service.name] = map_service

        # Add map config path to meta-config
        with open(self.map_services['_meta_config'], 'a') as meta_config:
            meta_config.write('\n'+config_path)
