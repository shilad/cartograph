import types
from ConfigParser import SafeConfigParser

SERVER_CONFIG = None

def create(path):
    """
    Creates a new server config from the specified path
    """
    conf = SafeConfigParser()
    with open(path, "r") as configFile:
        conf.readfp(configFile)

    def getForDataset(target, datasetName, section, key):
        return target.get(section, key).replace('__DATASET__', datasetName)

    conf.getForDataset = types.MethodType(getForDataset, conf)

    return conf


def init(path='./conf/default_server.conf'):
    """
    Initializes the active global server config using the specified path
    """
    global SERVER_CONFIG

    SERVER_CONFIG = create(path)

    return SERVER_CONFIG


def get():
    global SERVER_CONFIG

    if not SERVER_CONFIG:
        init()

    assert(SERVER_CONFIG)

    return SERVER_CONFIG
