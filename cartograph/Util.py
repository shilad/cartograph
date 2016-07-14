from collections import defaultdict
import codecs
import numpy as np
import sys
import os


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


# def write_tsv(filename, headers, data):
#     with open(filename, "w") as f:
#         s = ("\t".join(headers) + "\n").encode("utf-8")
#         f.write(s)
#         for row_num in range(len(data[0])):
#             row = [col[row_num] for col in data]
#             s = ("\t".join(map(unicode, row)) + "\n").encode("utf-8")
#             f.write("%s\t%s" % (row_num, s))

def read_zoom(filename):
    values = defaultdict(dict)
    with open(filename) as f:
        for line in f:
            tokens = line.split('\t')
            zoom = tokens[0]
            denom = tokens[1][:-1]
            values[zoom] = denom
    return values


def read_features(sampleSize=None, *files):
    values = defaultdict(dict)
    for fn in files:
        with open(fn, "r") as f:
            content = f.readlines()[1:]
            content = [line.split("\t") for line in content]
            content.sort(key=lambda x: x[0])

            fields = [s.strip() for s in f.readline().split('\t')]
            if fields[-1] == 'vector':  # SUCH A HACK!
                count = 0
                for line in content:
                    count += 1
                    id = line[0]
                    if sampleSize is None or count < sampleSize:
                        values[id]['vector'] = np.array([float(t.strip()) for t in line[1:]])

            else:
                count = 0
                for line in content:
                    count += 1
                    if line[1][-1] == '\n':
                        line[1] = line[1][:-1]
                    if len(line) == len(fields):
                        id = line[0]
                        if sampleSize is None or count <= sampleSize:
                            values[id].update(zip(fields[1:], line[1:]))
                    else:
                        sys.stderr.write('invalid line %s in %s\n' % (`line`, `fn`))
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

        content = zip(indexList, data)
        content.sort(key=lambda x: x[0])
        for i in range(len(data)):
            data[i] = str(data[i])
            if data[i][-1] != "\n":
                data[i] += "\n"
            writeFile.write("%s\t%s" % (indexList[i], data[i]))


def sort_tsv(filename):
    ctime = os.path.getctime(filename)
    mtime = os.path.getmtime(filename)
    with open(filename, "r") as f:
        content = f.readlines()
        content = [line.split("\t") for line in content]
        header = content[0]
        content = content[1:]
        content.sort(key=lambda x: x[0])

    with open(filename, "w") as f:
        f.write("%s\t%s" % (header[0], header[1]))
        for line in content:
            if len(line) < 2:
                print line
            if content[1][-1] != "\n":
                content[1] += "\n"
            f.write("%s\t%s" % (line[0], line[1]))

    os.utime(filename, (ctime, mtime))



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


''' TODO: REFACTOR ME
def append_tsv(filename, header, indexList, *data):
    for index, dataList in enumerate(data):
        if len(dataList) != len(data[0]):
            raise InputError(index, "Lists must match to map together")
    with open(filename, "a") as writeFile:
        writeFile.write("\t".join(header) + "\n")
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
'''


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

if __name__=='__main__':

    sort_by_percentile(4)

