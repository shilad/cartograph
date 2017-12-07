import mimetypes
import subprocess

import shutil

from cartograph.MapConfig import createConf
from cartograph.server.globalmaptiles import GlobalMercator

mimetypes.init()

def getMimeType(path):
    if path.endswith('.topojson'):
        return 'application/json'
    elif path.endswith('.yaml'):
        return 'text/plain'
    else:
        (mtype, _) = mimetypes.guess_type(path)
        if mtype:
            return mtype
        else:
            raise Exception, 'Could not infer mimetype for path ' + `path`


_mercator = GlobalMercator()


def tileExtent(z, x, y):
    tx = x
    ty = 2 ** z - 1 - y  # tms coordinates
    (lat0, long0, lat1, long1) = _mercator.TileLatLonBounds(tx, ty, z)
    return (long0, lat0, long1, lat1)


import errno
import os

def pid_exists(pid):
    """Check whether pid exists in the current process table.
    UNIX only.
    from https://stackoverflow.com/a/6940314
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True


def build_map(server_config_path, map_config_path, input_path):
    """Build the map config file at config_path and output the build log/errors to files in its baseDir
    :param config_path: full path to the config file of the map to be built
    """

    # Extract the location of the base dir from the config file
    config = createConf(map_config_path)
    output_path = config.get('DEFAULT', 'externalDir')
    input_path2 = os.path.join(output_path, 'input.tsv')
    shutil.copy2(input_path, input_path2)

    # Set up the environment variables
    python_path = os.path.expandvars('$PYTHONPATH:.:./cartograph')
    working_dir = os.getcwd()
    exec_path = os.getenv('PATH')

    env = {'CARTOGRAPH_CONF': map_config_path, 'PYTHONPATH': python_path, 'PWD': working_dir, 'PATH': exec_path}
    log = open(os.path.join(output_path, 'build.log'), 'w')

    args = ['./bin/make_map.sh',
            '--server_conf', server_config_path,
            '--map_conf', map_config_path,
            '--input', input_path2]

    log.write('Running command sequence:\n')
    for (k, v) in env.items():
        log.write(' %s=%s' % (k, v))
    log.write(' ' + ' '.join(args))
    log.write('\n\n\n')


    # Build it!
    proc = subprocess.Popen(args,
                            env=env,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            preexec_fn=os.setpgrp)

    if proc.poll() and proc.returncode != 0:
        raise OSError, 'Luigi build exited with status %d! Log available in %s/build.log' % (proc.returncode, output_path)



if __name__ == '__main__':
    build_map('./data/conf/summer2017_simple.txt')
