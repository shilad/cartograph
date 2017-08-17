import codecs
import csv
import json
import os
import pipes
from ConfigParser import SafeConfigParser
import falcon
import pandas
from cartograph.server.Map import Map


# TODO: move all these server-level configs into the meta config file
# This may be a good time to rethink the format of that file as well.
# Should it also use SafeConfig
from cartograph.server.ServerUtils import pid_exists, build_map

BASE_LANGUAGE = 'simple'
USER_CONF_DIR = 'data/conf/user/'
BASE_PATH = './data/ext/'

STATUS_NOT_STARTED = 'NOT_STARTED'
STATUS_RUNNING = 'RUNNING'
STATUS_FAILED = 'FAILED'
STATUS_SUCCEEDED = 'SUCCEEDED'

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

    # TODO: adjust parameters for size of dataset:
    # - numClusters
    # - perplexity
    # - water level
    # - min_num_in_cluster
    # - num_contours
    # - contour_bins

    return config_path


def gen_data(source_dir, target_path, articles):
    """Generate the data files (i.e. "TSV" files) for a map with a string of articles <articles>
    in the directory at target_path.

    :param target_path: path to directory (that will be created) to be filled with data files
    :param articles: file object of user data; must be TSV w/ headers on first row; 1st column must be article titles
    :return: tuple (set of article titles not found in source data, list of column headers excluding first column)
    """

    # Generate dataframe of user data
    user_data = pandas.read_csv(articles, delimiter='\t')
    first_column = list(user_data)[0]
    user_data.set_index(first_column, inplace=True)  # Assume first column contains titles of articles
    all_articles = set(user_data.index.values)

    # Generate dataframe of names to IDs
    names_file_path = os.path.join(source_dir, 'names.tsv')
    names_to_ids = pandas.read_csv(names_file_path, delimiter='\t', index_col='name', dtype={'id': object})
    # TODO: COnsider strings in data type above

    # Append internal ids with the user data; set the index to 'id';
    # preserve old index (i.e. 1st column goes to 2nd column)
    user_data_with_internal_ids = user_data.merge(names_to_ids, left_index=True, right_index=True, how='inner')
    good_articles = set(user_data_with_internal_ids.index)
    user_data_with_internal_ids[first_column] = user_data_with_internal_ids.index
    user_data_with_internal_ids.set_index('id', inplace=True)

    # Generate list of IDs for article names in user request, generate set of articles for which no id could be found
    ids = set(user_data_with_internal_ids.index.values)
    bad_articles = all_articles - good_articles

    # Create the destination directory (if it doesn't exist already)
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # For each of the primary data files, filter it and output it to the target directory
    for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv']:
        filter_tsv(source_dir, target_path, ids, filename)

    # Replace internal ids in metric with external ids
    # TODO: Change metric to use internal ids (maybe)
    external_ids = pandas.read_csv(
        os.path.join(target_path, 'ids.tsv'),
        sep='\t',
        dtype={'id': object, 'externalId': object}  # read ids as strings
    )
    external_ids.set_index('id', inplace=True)
    user_data_with_external_ids = user_data_with_internal_ids.merge(external_ids, left_index=True,
                                                                    right_index=True, how='inner')
    user_data_with_external_ids.set_index('externalId', inplace=True)
    user_data_with_external_ids.to_csv(os.path.join(target_path, 'metrics.tsv'), sep='\t')

    data_columns = list(user_data)

    return (bad_articles, data_columns)  # FIXME: Including data_columns is maybe coupling


def add_layer(config_path, info, metric_df):
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

    if info['field'] == 'Clusters': return # TODO: Fix this up

    # Add layers
    c = SafeConfigParser()
    c.read(config_path)

    id = info['id']
    field = info['field']

    # Configure settings for a metric
    metric_settings = {
        'type': info['datatype'],
        'path': metric_df.path,
        'field': field,
        'colorCode': info['colorScheme']
    }

    # Load user data to mine for appropriate values
    metric_type = info['datatype']

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

    # Define new metric in config file
    c.set('Metrics', id, json.dumps(metric_settings))

    active = []
    if c.has_option('Metrics', 'active'):
        active = c.get('Metrics', 'active').split()
    c.set('Metrics', 'active', ' '.join(active + [id]))

    with open(config_path, 'w') as f:
        c.write(f)


class AddMapService:
    """A service to allow clients to build maps from already-uploaded data files (see UploadService). When POSTed to,
    this service will attempt to filter the appropriate (TSV) data files from a parent map, which is currently
    hard-coded as 'simple'. It will then create a config file and launch the build process from that config file. Once
    built, it will add the path of that config file to the active multi-config file and the list of active maps in
    self.map_services.
    """

    def __init__(self, server_config, map_services):
        """Initialize an AddMapService, a service to allow the client to build maps from already uploaded data files.
        When the client POSTs to this service, if there is a file in the upload directory of the matching name (i.e.
        map_name.tsv), this service will build a map with that name from that file.

        :param server_config: ServerConfig object
        :param map_services: (dict) a reference to dictionary whose keys are map names and values are active MapServices
        :param upload_dir: (str) path to directory containing uploaded map data files
        """
        self.conf = server_config
        self.map_services = map_services
        self.upload_dir = server_config.get('DEFAULT','upload_dir')

    def on_post(self, req, resp):
        """Making a POST request to this URL will cause the server to attempt to build a map from a file in the
        upload_dir by the name of <map_name>.tsv. If no such file exists, this service will respond with a 404.

        {
           "mapId":"zoo",
           "mapTitle":"Foo",
           "email":"shilad@gmail.com",
           "layers":[
              {
                 "field":"Clusters",
                 "id":"clusters",
                 "title":"Thematic Clusters",
                 "description":"This visualization shows groups of thematically related articles.",
                 "datatype":"qualitative",
                 "numColors":"7"
              },
              {
                 "field":"Popularity",
                 "id":"pop",
                 "title":"Popularity",
                 "description":"Popularity",
                 "datatype":"sequential",
                 "numColors":"3"
              }
           ]
        }

        """
        body = req.stream.read()
        js = json.loads(body)
        map_id = js['mapId']

        # Make sure the server is in multi-map mode
        # FIXME: This should be a better error
        assert self.map_services['_multi_map']

        # Try to open map data file, raise 404 if not found in upload directory
        map_file_name = map_id + '.tsv'
        if map_file_name not in os.listdir(self.upload_dir):
            raise falcon.HTTPNotFound
        input_file = open(os.path.join(self.upload_dir, map_file_name), 'r')

        output_dir = os.path.join(BASE_PATH, 'user/', map_id)
        # FIXME: Change 'simple' to a map name selected by the user
        bad_articles, data_columns = gen_data(os.path.join(BASE_PATH, BASE_LANGUAGE), output_dir, input_file)
        config_path = gen_config(map_id, data_columns)

        # Read in the metric file and add layers
        config = SafeConfigParser()
        config.read(config_path)
        layer_tsv = os.path.join(config.get('DEFAULT', 'externalDir'), 'metrics.tsv')
        layer_df = pandas.read_csv(layer_tsv , sep='\t')
        layer_df.path = layer_tsv
        for layer in js['layers']:
            add_layer(config_path, layer, layer_df)

        # Build from the new config file
        build_map(config_path)

        # Add urls to server that point to new map
        map_service = Map(config_path)
        self.map_services[map_service.name] = map_service

        # Add map config path to meta-config file
        with open(self.map_services['_meta_config'], 'a') as meta_config:
            meta_config.write('\n'+config_path)

        # Clean up: delete the uploaded map data file
        os.remove(os.path.join(self.upload_dir, map_file_name))

        # Return helpful information to client
        resp.body = json.dumps({
            'success' : True,
            'map_name': map_id,
            'bad_articles': list(bad_articles),
            'data_columns': data_columns
        })

    def get_status(self, map_id):
        """
        Returns the status of map creation for the specified map.
        Double checks that maps that should be running ARE actually running.
        """
        path = self.conf.getForDataset(map_id, 'ext_dir') + '/status.txt'
        if not os.path.isfile(path):
            return STATUS_NOT_STARTED
        tokens = open(path).read().strip().split()
        status = tokens[0]
        if status == STATUS_RUNNING:
            pid = tokens[1]
            if not pid_exists(int(pid)):
                status = STATUS_FAILED
        return status

    def get_logs(self, map_id):
        """
        Returns the luigi output log for the given map, or empty string if it doesn't exist
        """
        path = self.conf.getForDataset(map_id, 'ext_dir') + '/build.log'
        if not os.path.isfile(path):
            return ''
        return open(path).read()

    def on_get(self, request, response, map_id):
        pass




