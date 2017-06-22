import csv
import falcon
import os
import string
import codecs
import pipes
from cartograph.server.MapService import MapService

USER_CONF_DIR = 'data/conf/user/'
BASE_PATH = './data/ext/'
SOURCE_DIR = os.path.join(BASE_PATH, 'simple/')  # Path to source data (which will be pared down for the user)
ACCEPTABLE_MAP_NAME_CHARS = string.uppercase + string.lowercase


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
    :param ids: an iterable of the ids
    :param filename: the name of the file in <source_dir> to be filtered into a file of the same name in <target_dir>
    :return:
    """

    with codecs.open(os.path.join(source_dir, filename), 'r') as read_file, \
            codecs.open(os.path.join(target_dir, filename), 'w') as write_file:
        popularities_reader = csv.reader(read_file, delimiter='\t')
        popularities_writer = csv.writer(write_file, delimiter='\t', lineterminator='\n')
        popularities_writer.writerow(popularities_reader.next())  # Transfer the header
        for row in popularities_reader:
            if row[0] in ids:
                popularities_writer.writerow(row)


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
        for c in map_name:
            assert c in ACCEPTABLE_MAP_NAME_CHARS

        if not os.path.exists(USER_CONF_DIR):
            os.makedirs(USER_CONF_DIR)

        # Generate dictionary of article names to IDs
        # TODO: is there a way to do this once (instead of once per POST)?
        names_path = os.path.join(SOURCE_DIR, 'names.tsv')
        name_dict = {}
        with codecs.open(names_path, 'r') as names:
            names_reader = csv.reader(names, delimiter='\t')
            for row in names_reader:
                name = unicode(row[1], encoding='utf-8')
                name_dict[name] = row[0]

        # Generate list of IDs for article names in user request
        ids = []
        for term in post_data['articles'].split('\r\n'):
            try:
                ids += [name_dict[term]]  # Attempts to find entry in dict of Articles to IDs
            except KeyError:
                # TODO: The following line is for debugging; proper behavior yet to be defined
                resp.body += 'NO MATCH FOR TERM: %s\n' % (term,)

        # Create the destination directory (if it doesn't exist already)
        target_path = os.path.join(BASE_PATH, 'user/', map_name)
        if not os.path.exists(target_path):
            os.makedirs(target_path)

        # For each of the data files, filter it and output it to the target directory
        for filename in ['ids.tsv', 'links.tsv', 'names.tsv', 'popularity.tsv', 'vectors.tsv']:
            filter_tsv(SOURCE_DIR, target_path, ids, filename)

        # Generate a new conf file
        with open('./data/conf_template.txt', 'r') as conf_template_file:
            conf_template = string.Template(conf_template_file.read())
        config_filename = '%s.txt' % pipes.quote(map_name)
        config_path = os.path.join(USER_CONF_DIR, config_filename)
        with open(config_path, 'w') as config_file:
            config_file.write(conf_template.substitute(name=map_name))

        # Build from the new conf file
        os.system("CARTOGRAPH_CONF=""%s"" PYTHONPATH=$PYTHONPATH:.:./cartograph luigi --module cartograph ParentTask --local-scheduler" % config_path)

        # Add urls to new map
        map_service = MapService(config_path)
        self.map_services[map_service.name] = map_service

        # Add map config path to meta-config
        with open(self.map_services['_meta_config'], 'a') as meta_config:
            meta_config.write('\n'+config_path)
