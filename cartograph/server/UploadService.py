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
    def __init__(self, server_config, dispatcher):
        """
        Creates a new service to handle data uploads.
        Args:
            server_config: ServerConfig object
            dispatcher: Map Dispatcher
        """
        self.server_config = server_config
        self.dispatcher = dispatcher
        self.upload_dir = server_config.get('DEFAULT', 'upload_dir')

        if not os.path.isdir(self.upload_dir):
            os.makedirs(self.upload_dir)

    def on_post(self, req, resp):
        resp.body = ''

        # Check the map name and make sure the dest file is empty
        map_id = req.get_param('map-id')
        try:
            check_map_id(map_id, self.dispatcher)
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
    columnTypes = []
    for i, col in enumerate(df.columns):

        # Todo: Move numclasses into this dictionary
        typeInfo = {'sequential': False,
                    'diverging': False,
                    'qualitative': False,
                    'title': False,
                    'numUnique': -1,
                    'name': str(col),
                    'values': [],
                    'range' : [],
                    'num' : 0}


        typeInfo['num'] = len(df[col]) - df[col].isnull().sum()
        typeInfo['numUnique'] = df[col].nunique()
        if i == 0:
            typeInfo['title'] = True
        else:
            if typeInfo['numUnique'] <= 12:
                typeInfo['qualitative'] = True
                typeInfo['values'] = sorted(x for x in df[col].unique() if type(x) == float and np.isfinite(x))


            dt = df[col].dtype
            if dt in (np.str, np.object):
                if df[col].nunique() > 12:
                    pass
            elif dt in (np.int64, np.float64):
                typeInfo['sequential'] = True
                typeInfo['diverging'] = True
                if df[col].nunique() > 12:
                    typeInfo['range'] = [df[col].min(), df[col].max()]
            else:
                raise ValueError('unknown type: ' + str(dt))
        columnTypes.append(typeInfo)

    return columnTypes


def check_map_id(map_id, dispatcher):
    """Check that map_name is not already in dispatcher and that all of its characters are in
    the list of acceptable characters. If any of these conditions is not met, this will raise a
    ValueError with an appropriate message.

    :param map_id: Name of the map to check
    :param dispatcher: Map dispatcher
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
    if dispatcher.has_map(map_id):
        raise ValueError('Map name "%s" already in use for an active map!' % (map_id,))
