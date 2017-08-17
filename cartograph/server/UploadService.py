import json
import string

import logging
import numpy as np
import os
import pandas as pd
import shutil


ACCEPTABLE_MAP_NAME_CHARS = string.uppercase + string.lowercase + '_' + string.digits

logger = logging.getLogger('cartograph.upload')


class UploadService:
    def __init__(self, server_config, map_services):
        """
        Creates a new service to handle data uploads.
        Args:
            server_config: ServerConfig object
            map_services: Dictionary from map name to map
        """
        self.server_config = server_config
        self.map_services = map_services
        self.upload_dir = server_config.get('DEFAULT', 'upload_dir')

        if not os.path.isdir(self.upload_dir):
            os.makedirs(self.upload_dir)

    def on_post(self, req, resp):
        resp.body = ''

        # Check the map name and make sure the dest file is empty
        map_id = req.get_param('map-id')
        try:
            check_map_id(map_id, self.map_services)
        except ValueError as e:
            resp.body = json.dumps({
                'success': False,
                'map_name': map_id,
                'error': str(e),
                'stacktrace': repr(e),
            })
            return

        # If file exists remove it
        dest = self.upload_dir + '/' + map_id + '.tsv'
        if os.path.isfile(dest):
            os.unlink(dest)

        # Write the supplied text or file to a temporary tsv
        articles_file = req.get_param('file')
        articles_text = req.get_param('file_text')
        if articles_file not in (None, ''):
            with open(dest, 'wb') as f:
                shutil.copyfileobj(articles_file.file, f)
        elif articles_text not in (None, ''):
            with open(dest, 'wb') as f:
                f.write(articles_text)
                f.close()
        else:
            raise ValueError, "Missing article both text and upload file"

        # Scan the TSV for field names.
        # TODO: This should handle lots of things:
        # - Different encodings
        # - Ignore duplicate titles
        # - Files that are too long
        # - Files that are irregularly formatted (be gentle with errors)
        try:
            df = pd.read_csv(dest, sep='\t')
            nrows, ncols = df.shape
            cols = df.columns.tolist()
            assert (len(cols) == ncols)

            columns = detectDataTypes(df)

            resp.body = json.dumps({
                'success': True,
                'map_name': map_id,
                'columns': columns,
                'num_rows': nrows,
            })
        except ValueError as e1:
            logger.exception("Upload file: value error")
            resp.body = json.dumps({
                'success': False,
                'map_name': map_id,
                'error': str(e1),
                'stacktrace': repr(e1),
            })

        except TypeError as e2:
            logger.exception("Upload file: type error")
            resp.body = json.dumps({
                'success': False,
                'map_name': map_id,
                'error': str(e2),
                'stacktrace': repr(e2),
            })

def detectDataTypes(df):
    # TODO: Make valid columns available, hide invalid columns
    types = []
    for i, col in enumerate(df.columns):

        # Todo: Move numclasses into this dictionary
        type = {'sequential': False,
                'diverging': False,
                'qualitative': False,
                'title': False,
                'numUnique': -1,
                'name': str(col),
                'values': [],
                'range' : [],
                'num' : 0}


        type['num'] = len(df[col]) - df[col].isnull().sum()
        type['numUnique'] = df[col].nunique()
        if i == 0:
            type['title'] = True
        else:
            if type['numUnique'] <= 12:
                type['qualitative'] = True
                type['values'] = sorted(df[col].unique())

            dt = df[col].dtype
            if dt in (np.str, np.object):
                if df[col].nunique() > 12:
                    raise ValueError('too many classes for qualitative data: ' + str(df[col].nunique()))
            elif dt in (np.int64, np.float64):
                type['sequential'] = True
                type['diverging'] = True
                if df[col].nunique() > 12:
                    type['range'] = [df[col].min(), df[col].max()]
            else:
                raise ValueError('unknown type: ' + str(dt))
        types.append(type)

    return types


def check_map_id(map_id, map_services):
    """Check that map_name is not already in map_services and that all of its characters are in
    the list of acceptable characters. If any of these conditions is not met, this will raise a
    ValueError with an appropriate message.

    :param map_id: Name of the map to check
    :param map_services: (pointer to) dictionary whose keys are names of currently active maps
    """
    # FIXME: This does not check if a non-user-generated non-active map with the same name \
    # FIXME: already exists. I can't think of an easy way to fix that.

    # Prevent map names with special characters (for security/prevents shell injection)
    bad_chars = set()
    for c in map_id:
        if c not in ACCEPTABLE_MAP_NAME_CHARS:
            bad_chars.add(c)
    if bad_chars:
        bad_char_string = ', '.join(['"%s"' % (c,) for c in bad_chars])
        good_char_string = ', '.join(['"%s"' % (c,) for c in ACCEPTABLE_MAP_NAME_CHARS])
        raise ValueError('Map name "%s" contains unacceptable characters: [%s]\n'
                         'Accepted characters are: [%s]' % (map_id, bad_char_string, good_char_string))

    # Prevent adding a map with the same name as a currently-served map
    # This will prevent adding user-generated maps with the same names as
    # active non-user-generated maps, e.g. "simple" or "en"
    if map_id in map_services.keys():
        raise ValueError('Map name "%s" already in use for an active map!' % (map_id,))
