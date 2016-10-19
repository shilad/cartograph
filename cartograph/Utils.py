from collections import defaultdict
import codecs
import numpy as np
import sys

import psycopg2


def read_tsv(filename):
    with codecs.open(filename, "r", encoding="utf-8") as f:
        headers = f.readline().rstrip("\n").split("\t")
        data = {header: [] for header in headers}
        for line in f:
            row = line.rstrip("\n").split("\t")
            for i, string in enumerate(row):
                data[headers[i]].append(string)
    return data


def read_wikibrain_vecs(path):
    """
    We need this function since the file is organized by rows, not columns
    """
    matrix = []
    with open(path, "r") as vecs:
        vecs.readline()
        for line in vecs:
            matrix.append(map(float, line.rstrip("\n").split("\t")))
    return matrix


def read_features(*files, **kwargs):
    id_set = kwargs.get('id_set', None)
    values = defaultdict(dict)
    required = kwargs.get('required', [])
    for fn in files:
        with open(fn, "r") as f:
            fields = [s.strip() for s in f.readline().split('\t')]
            if fields[-1] == 'vector': # SUCH A HACK!
                for line in f:
                    tokens = line.split('\t')
                    id = tokens[0]
                    if id_set == None or id in id_set:
                        values[id]['vector'] = np.array([float(t.strip()) for t in tokens[1:]])
            if fields[-1] == 'coords':
                for line in f:
                    tokens = line.split('\t')
                    id = tokens[0]
                    values[id]['coords'] = np.array([float(t.strip()) for t in tokens[1:]])
            else:
                for line in f:
                    if line[-1] == '\n': line = line[:-1]
                    tokens = line.split('\t')
                    if len(tokens) == len(fields):
                        id = tokens[0]
                        if id_set == None or id in id_set:
                            values[id].update(zip(fields[1:], tokens[1:]))
                    else:
                        sys.stderr.write('invalid line %s in %s\n' % (`line`, `fn`))
    if required:
        return {
            id : record
            for (id, record) in values.items()
            if all((k in record) for k in required)
        }
    else:
        return values


def write_tsv(filename, header, indexList, *data):
    for index, dataList in enumerate(data):
        if len(dataList) != len(data[0]):
            raise InputError(index, "Lists must match to map together")
    with open(filename, "w") as writeFile:
        writeFile.write("\t".join(header) + "\n")
        if len(data) > 1:
            data = zip(*data)
            data = ["\t".join([str(val) for val in dataPt]) for dataPt in data]
        else:
            data = data[0]
        for i in range(len(data)):
            data[i] = str(data[i])
            if data[i][-1] != "\n":
                data[i] += "\n"
            writeFile.write("%s\t%s" % (indexList[i], data[i]))
        writeFile.close()

def append_to_tsv(parentName, writeName, *data):
    with open(parentName, "r") as parentFile:
        lines = parentFile.readlines()
        header = lines[0]
        indices = header.split("\t")
        lastIndex = len(lines) - 1

    assert(len(data) == len(indices) - 1)

    with open(writeName, "w") as writeFile:
        for line in lines:
            writeFile.write(line)

        if len(data) > 1:
            data = zip(*data)
            data = ["\t".join([str(val) for val in dataPt]) for dataPt in data]
        else:
            data = data[0]

        for i in range(len(data)):
            index = lastIndex + i + 1
            data[i] = str(data[i])
            if data[i][-1] != "\n":
                data[i] += "\n"
            writeFile.write("%s\t%s" % (index, data[i]))


def sort_by_feature(articleDict, featureName, reverse=True):
    allArticles = []
    if featureName not in articleDict[articleDict.keys()[0]]:
        raise InputError(featureName, "Feature does not exist")
    for key in articleDict:
        allArticles.append((key, articleDict[key]))
    allArticles.sort(key=lambda x: float(x[1][featureName]), reverse=reverse)
    return allArticles

def sort_by_percentile(numBins):
    unitStep = 100/numBins
    percentileDataValue = defaultdict(dict)
    for i, percentile in enumerate(list(range(0,100,unitStep))):
        print(i)
        print("=========")
        print(i+1)
        # np.percentile(percentileList, (i, i+1))


def pg_cnx(config):
    return psycopg2.connect(
        dbname=config.get('PG', 'database'),
        host=config.get('PG', 'host'),
        user=config.get('PG', 'user'),
        password=config.get('PG', 'password'),
    )

class InputError(Exception):
    """Exception raised for errors in the input.

    Attributes:
        expr -- input expression in which the error occurred
        msg  -- explanation of the error
    """

    def __init__(self, expr, msg):
        self.expr = expr
        self.msg = msg

def calc_area(points):
    unzipped = zip(*points)
    x = unzipped[0]
    y = unzipped[1]
    # Shoelace Algorithm (a la Stackoverflow)
    return 0.5 * np.abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1)))


def zoomMeters(zoom):
    return 156543.03 / (2 ** zoom)

if __name__=='__main__':

    sort_by_percentile(4)

