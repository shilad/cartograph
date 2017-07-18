import pandas as pd
import numpy as np
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
    count = -1
    rows = []
    cols = []
    vals = []
    for pairing in (sequence):
        src, roadDict = pairing
        for dest in sorted(roadDict):
            cols.append(dest)
            vals.append(roadDict[dest])
        rows.append(count+1)
        count+=len(roadDict)

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
    # def __init__(self, outputdir, origEdgesPath):
    #     #testSparseMatrix = pd.read_csv(origEdgesPath, sep=" ", skiprows=[0], header=None, names=edgeList,)
    #     testMatrix = pd.read_csv(origEdgesPath, sep=" ", header=None, skiprows=[0], names=["Src", "Dst"], dtype=[("Src", "int32"), ("Dst", "int32")])
    #     colList = testMatrix["Dst"].tolist()
    #     #colList is a list where for any given index i which stands for a row, colList gives the Dst associated with that given row
    #     rowVals = testMatrix["Src"].tolist()
    #     rowList = []
    #     prevRowID = None
    #     for i in range(0,len(rowVals)):
    #         if rowVals[i] != prevRowID:
    #             rowList.append(i)
    #             prevRowID = rowVals[i]
    #     rowMemShape = np.asarray(rowList).shape
    #     colMemShape = np.asarray(colList).shape
    #     savePathRow=outputdir+"/row_indexes.mmap"
    #     savePathCol=outputdir+"/columns.mmap"
    #     rowMap = np.memmap(savePathRow, dtype='int32', mode="w+", shape=rowMemShape)
    #     rowMap[:] = np.asarray(rowList)
    #     colMap = np.memmap(savePathCol, dtype='int32', mode="w+", shape=colMemShape)
    #     colMap[:] = np.asarray(colList)
    #     print(rowMap)
    #     print(colMap.dtype)

    def __init__(self, outpudDir):
        print("jek you bonobo!")


outputdir = "/Users/sen/PycharmProjects/CartoGraphRoadAPI/DataFiles"
sequence = createSequence(origEdgesPath)
startTime = time.time()
writeSparseMatrix(sequence, outputdir)
#peter = MMappedSparseMatrix(outputdir, origEdgesPath)
endTime = time.time()
timepassed = endTime - startTime
print("Time elapsed: " + str(timepassed))