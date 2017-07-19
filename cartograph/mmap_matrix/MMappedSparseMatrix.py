import pandas as pd
import numpy as np
from scipy.sparse import csc_matrix
import time
origEdgesPath = "/Users/sen/PycharmProjects/CartoGraphRoadAPI/DataFiles/OriginalEdges.txt"

def createSequence(origEdgesPath):
    sequenceDict = {} #yeah I know this isn't efficient but I just need something to test
    with open(origEdgesPath, 'r') as ptbe:
        for line in ptbe:
            lst = line.split()
            if len(lst) == 1: continue
            src = int(lst[0])
            dst = int(lst[1])
            if src in sequenceDict:
                sequenceDict[src][dst] = 1
            else:
                sequenceDict[src] = {dst:1}
    sequenceList = []
    for key in sorted(sequenceDict): #sorting here preserves order, uhh yeah.
        sequenceList.append((key, sequenceDict[key]))
    return sequenceList #This should be hopefully the set of tuples, (row, vals) where val is a dictionary with weight vals

def writeSparseMatrix(sequence, outputdir):
    print("ayy jek")
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
    print(rows)

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
        print("jek you bonobo!")
        colAddress = outputdir+"/columns.mmap"
        rowAddress = outputdir+"/row_indexes.mmap"
        valAddress = outputdir+"/values.mmap"
        shapesAddress = outputdir+"/shape.txt"
        self.rowMap = np.memmap(rowAddress, dtype="int32", mode="r+")
        self.colMap = np.memmap(colAddress, dtype="int32", mode="r+")
        self.valMap = np.memmap(valAddress, dtype="int32", mode="r+")

    #Seems to work. Still need to sort out index assignment. YOU MUST SPECIFY IF INDEX OR EDGEID BASED
    def get_row_as_np(self, index=-1, edgeId = -1):
        print("JEK")
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

    def get_row_as_dict(self, index=-1, edgeId = -1):
        print("TEH")
        if edgeId != -1:
            index = edgeId -1
        else:
            if edgeId == -1 and index == -1:
                print("Error, please specify index or edgeId value")

        startIndex = self.rowMap[index]
        endIndex = self.rowMap[index+1]

        edgeValDict = {}
        for i in range(startIndex, endIndex):
            edgeValDict[self.colMap[i]] = self.valMap[i]
        return edgeValDict

    #seems to work sort of... the 4 test vals for edgeId 1 seem to clear.
    def get_row_as_csc(self, index=-1, edgeId = -1):
        print("STEK")
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
        print("LINDEN")
        #rowMap needs to be size of colmap
        rowVals = []
        for i in range(0, self.rowMap.size-1):
            for z in range(self.rowMap[i], self.rowMap[i+1]):
                rowVals.append(i+1)
        for i in range(self.rowMap[-1], self.colMap.size):
            rowVals.append(self.rowMap.size+1)
        rowNp = np.asarray(rowVals)
        return csc_matrix((self.valMap, (rowNp, self.colMap)), shape=(rowNp.size, self.colMap.size))

outputdir = "/Users/sen/PycharmProjects/CartoGraphRoadAPI/DataFiles"
sequence = createSequence(origEdgesPath)
startTime = time.time()
endTime = time.time()
timepassed = endTime - startTime
print("Time elapsed: " + str(timepassed))