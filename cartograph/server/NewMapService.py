import csv
import StringIO

import falcon
import os
import string
import codecs
import pipes

import pandas

from cartograph.Utils import read_tsv, read_vectors
from cartograph.server.MapService import MapService

USER_CONF_DIR = 'data/conf/user/'
BASE_PATH = './data/ext/'
SOURCE_DIR = os.path.join(BASE_PATH, 'simple/')  # Path to source data (which will be pared down for the user)
ACCEPTABLE_MAP_NAME_CHARS = string.uppercase + string.lowercase


def gen_config(map_name, metric_type, field_name):
    """Generate the config file for a user-generated map named <map_name> and return a path to it

    :param map_name: name of new map
    :param metric_type: type of metric as a string, e.g. 'BIVARIATE' or 'COUNT'
    :param field_name: the name of the field in-file for the column whose values will be used for the metric
    :return: path to the newly-generated config file
    """
    TYPE_NAME = {'BIVARIATE': 'bivariate-scale'}

    # Prevent map names with special characters (for security/prevents shell injection)
    for c in map_name:
        assert c in ACCEPTABLE_MAP_NAME_CHARS

    if not os.path.exists(USER_CONF_DIR):
        os.makedirs(USER_CONF_DIR)

    # Generate a new conf file
    with open('./data/conf_template.txt', 'r') as conf_template_file:
        conf_template = string.Template(conf_template_file.read())
    if metric_type == 'NONE':
        with open('data/no_metric_template.txt', 'r') as metric_template_file:
            metric_section = metric_template_file.read()
    elif metric_type == 'BIVARIATE':
        with open('data/metric_template.txt', 'r') as metric_template_file:
            metric_section = string.Template(metric_template_file.read())\
                .substitute(metric_type=TYPE_NAME[metric_type], field_name=field_name,
                            metric_name=string.lower(field_name))
    elif metric_type == 'COUNT':
        raise NotImplementedError()
    config_filename = '%s.txt' % pipes.quote(map_name)
    config_path = os.path.join(USER_CONF_DIR, config_filename)
    assert not os.path.exists(config_path)  # Make sure no map config with this name exists
    with open(config_path, 'w') as config_file:
        config_file.write(conf_template.substitute(name=map_name, metric_section=metric_section))

    return config_path


def gen_data(map_name, articles_file, metric_type):
    """Generate the data files (i.e. "TSV" files) for a map named <map_name> and a string of articles <articles>.

    :param map_name: name of new map
    :param articles: list of exact titles of articles for new map
    :return: list of article titles for which there was no exact match in the existing dataset
    """
    # Generate dictionary of article names to IDs
    # TODO: is there a way to do this once (instead of once per POST)?
    names_path = os.path.join(SOURCE_DIR, 'names.tsv')
    name_dict = {}
    with codecs.open(names_path, 'r') as names:
        names_reader = csv.reader(names, delimiter='\t')
        for row in names_reader:
            name = unicode(row[1], encoding='utf-8')
            name_dict[name] = row[0]

    # Create the destination directory (if it doesn't exist already)
    target_path = os.path.join(BASE_PATH, 'user/', map_name)
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    # Generate data matrix
    data = []
    articles_reader = csv.reader(articles_file, delimiter='\t')
    header = articles_reader.next()
    for row in articles_reader:
        data.append(row)

    # Generate list of IDs for article names in user request
    ids = set()
    bad_articles = set()
    for row in data:
        title = row[0]
        try:
            ids.add(name_dict[title])  # Attempts to find entry in dict of Articles to IDs
        except KeyError:
            bad_articles.add(title)

    # For each of the data files, filter it and output it to the target directory
    for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv']:

        # Read the file into a dataframe (source_data)
        source_file_path = os.path.join(SOURCE_DIR, filename)
        if filename == 'vectors.tsv':
            source_data = read_vectors(source_file_path)
        else:
            source_data = pandas.read_csv(source_file_path, sep='\t', index_col='id')

        # Filter the dataframe
        filtered_data = source_data[source_data.index.isin(ids)]

        # Write the dataframe to the target file
        target_file_path = os.path.join(target_path, filename)
        # Treat vectors.tsv as a special case because it is *not* a true TSV (for some reason)
        if filename == 'vectors.tsv':
            source_data.index.name = 'id'  # FIXME: w/o this line, it comes out as 'index' (just in vectors.tsv)
            with open(target_file_path, 'w') as target_file:
                target_file.write('\t'.join([source_data.index.name] + list(source_data)) + '\n')
                for index, row in source_data.iterrows():
                    # str of the vector, each component separated by tabs
                    # FIXME: components should be in scientific notation
                    vector = '\t'.join([str(component) for component in row[0]])
                    target_file.write(str(index) + '\t' + vector + '\n')
        # For all other TSVs, just write them normally
        else:
            filtered_data.to_csv(target_file_path, sep='\t')

    return bad_articles


class AddMapService:

    def __init__(self, map_services):
        self.map_services = map_services

    def on_get(self, req, resp):
        resp.stream = open('./web/newMap.html', 'rb')
        resp.content_type = 'text/html'

    def on_post(self, req, resp):
        post_data = falcon.uri.parse_query_string(req.stream.read())
        resp.body = ''

        map_name = post_data['name']
        metric = post_data['metric']
        field_name = '' if metric == 'NONE' else post_data['field_name']
        # FIXME: non-ASCII compatible?
        articles_file = StringIO.StringIO(post_data['articles'])


        # Prevent adding a map with the same name as a currently-served map
        # This will prevent adding user-generated maps with the same names as
        # active non-user-generated maps, e.g. "simple" or "en"
        assert map_name not in self.map_services.keys()

        # TODO: Figure out what to do with <bad_articles>
        bad_articles = gen_data(map_name, articles_file, metric)
        config_path = gen_config(map_name, metric, field_name)

        # Build from the new config file
        os.system("CARTOGRAPH_CONF=""%s"" PYTHONPATH=$PYTHONPATH:.:./cartograph luigi --module cartograph ParentTask --local-scheduler" % config_path)

        # Add urls to new map
        map_service = MapService(config_path)
        self.map_services[map_service.name] = map_service

        # Add map config path to meta-config
        with open(self.map_services['_meta_config'], 'a') as meta_config:
            meta_config.write('\n'+config_path)
