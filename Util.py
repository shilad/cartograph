from collections import defaultdict
import codecs
import Constants
import numpy as np
import sys

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


def write_tsv(filename, headers, data):
    with open(filename, "w") as f:
        s = ("\t".join(headers) + "\n").encode("utf-8")
        f.write(s)
        for row_num in range(len(data[0])):
            row = [col[row_num] for col in data]
            s = ("\t".join(map(unicode, row)) + "\n").encode("utf-8")
            f.write(s)


def read_features(*files):
    values = defaultdict(dict)
    for fn in files:
        if fn == Constants.FILE_NAME_NUMBERED_VECS:
            with open(fn, "r") as f:
                f.readline()    # skip the header
                for line in f:
                    tokens = line.split('\t')
                    id = tokens[0]
                    values['vector'] = np.array([float(t.strip()) for t in tokens[1:]])
        else:
            with open(fn, 'r') as f:
                fields = [s.strip() for s in f.readline().split('\t')]
                for line in f:
                    if line[-1] == '\n': line = line[:-1]
                    tokens = line.split('\t')
                    if len(tokens) == len(fields):
                        id = tokens[0]
                        values[id].update(zip(fields[1:], tokens[1:]))
                    else:
                        sys.stderr.write('invalid line %s in %s\n' % (`line`, `fn`))
    return values
