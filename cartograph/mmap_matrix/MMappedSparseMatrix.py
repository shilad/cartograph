import pandas as pd
import numpy as np
from scipy.sparse import csc_matrix

def writeSparseMatrix(sequence, outputdir):
    #I can't seem to get the logic right, it's either one or two off each time. Partly because the line numbers in Original Edges are off but...
    count = 0
    rows = []
    cols = []
    vals = []
    for pairing in (sequence):
        src, roadDict = pairing
        for dest in sorted(roadDict):
            cols.append(dest)
            vals.append(roadDict[dest])
        rows.append(count)
        count += len(roadDict)
    #rows memmap conversion
    rowNp = np.asarray(rows)
    rowShape = rowNp.shape
    rowMap = np.memmap(outputdir+"/row_indexes.mmap", dtype='int32', mode="w+", shape=rowShape)
    rowMap[:] = rowNp
    rowMap.flush()

    #cols mmap conversion
    colNp = np.asarray(cols)
    colShape = colNp.shape
    colMap = np.memmap(outputdir+"/columns.mmap", dtype='int32', mode="w+", shape=colShape)
    colMap[:] = colNp
    colMap.flush()

    #vals mmap conversion
    valNp = np.asarray(vals)
    valShape = valNp.shape
    valMap = np.memmap(outputdir+"/values.mmap", dtype="int32", mode="w+", shape=valShape)
    valMap[:] = valNp
    valMap.flush()

    #draw Shapes!
    shapesFile = open(outputdir+"shape.txt", "w")
    shapesFile.write(str(len(rows))+" "+str(len(rows)))
    shapesFile.close()

class MMappedSparseMatrix():

    def __init__(self, outputDir):
        colAddress = outputDir+"/columns.mmap"
        rowAddress = outputDir+"/row_indexes.mmap"
        valAddress = outputDir+"/values.mmap"
        shapesAddress = outputDir+"/shape.txt"
        self.rowMap = np.memmap(rowAddress, dtype="int32", mode="r+")
        self.colMap = np.memmap(colAddress, dtype="int32", mode="r+")
        self.valMap = np.memmap(valAddress, dtype="int32", mode="r+")

    #Seems to work. Still need to sort out index assignment. YOU MUST SPECIFY IF INDEX OR EDGEID BASED
    def get_row_as_np(self, index=-1, edgeId = -1):
        #catch if want edgeId val instead of index
        if edgeId != -1:
            index = edgeId-1
        else:
            if edgeId == -1 and index == -1:
                print("Error, please specify index or edgeId value")

        startIndex = self.rowMap[index]
        endpoint = self.rowMap[index+1]
        print(str(startIndex) + " " + str(endpoint))
        rowVals = [0] * self.colMap.size
        for i in range(startIndex, endpoint):
            rowVals[self.colMap[i]] = self.valMap[i]
        rowNp = np.asarray(rowVals)
        return rowNp

    #returns a dictionary object for a given pointID, the keys are all the destination pointIDs, with vals being the Zpop
    def get_row_as_dict(self, index=-1, pointID = -1):
        if pointID != -1:
            index = pointID - 1
        else:
            if pointID == -1 and index == -1:
                print("Error, please specify index or edgeId value")

        startIndex = self.rowMap[index]
        endIndex = self.rowMap[index+1]

        edgeValDict = {}
        for i in range(startIndex, endIndex):
            edgeValDict[self.colMap[i]] = self.valMap[i]
        return edgeValDict

    #seems to work sort of... the 4 test vals for edgeId 1 seem to clear.
    def get_row_as_csc(self, index=-1, edgeId = -1):
        if edgeId != -1:
            index = edgeId -1
        else:
            if edgeId == -1 and index == -1:
                print("Error, please specify index or edgeId value")

        startIndex = self.rowMap[index]
        endpoint = self.rowMap[index+1]
        rowVals = [0] * self.colMap.size
        for i in range(startIndex, endpoint):
            rowVals[self.colMap[i]] = self.valMap[i]
        rowNp = np.asarray(rowVals)

        return csc_matrix((rowNp))

    def as_csr(self):
        #rowMap needs to be size of colmap
        rowVals = []
        for i in range(0, self.rowMap.size-1):
            for z in range(self.rowMap[i], self.rowMap[i+1]):
                rowVals.append(i+1)
        for i in range(self.rowMap[-1], self.colMap.size):
            rowVals.append(self.rowMap.size+1)
        rowNp = np.asarray(rowVals)
        return csc_matrix((self.valMap, (rowNp, self.colMap)), shape=(rowNp.size, self.colMap.size))


def test_memmaps(self):
    # pairs = [(4, 1247), (4, 39262), (5, 185), (5, 127), (7, 3), (7, 635), (8, 2557), (8, 39078), (10, 498), (10, 16736),
    #          (10, 75164), (2295, 35), (2295, 92)]
    # for src, dest in pairs:
    #     assert self.articlesZpop[src] * self.articlesZpop[dest] == self.get_row_as_dict(pointID=src)[dest]
    # assert 1 in self.get_row_as_dict(index=1)
    pairs = [(2317, 8926), (2317, 1641), (2322, 273), (2324, 8125), (14980, 97), (14980, 38212), (14984, 25144),
             (14984, 5190), (15171, 5), (15171, 322), (97017, 1475)]
    for src, dst in pairs:
        print(src, dst)
        assert dst in self.get_row_as_dict(pointID=src)
