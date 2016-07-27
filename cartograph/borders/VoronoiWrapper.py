from scipy.spatial import Voronoi
from collections import defaultdict
from Vertex import Vertex


class VoronoiWrapper:

    def __init__(self, x, y, clusterLabels, waterLabel):
        self.points = zip(x, y)
        self._clusterLabels = clusterLabels
        self.waterLabel = waterLabel
        self.vor = Voronoi(self.points)

        # cluster label -> vertex index -> list of adjacent vertices
        self.edgeRidgeDict = defaultdict(lambda: defaultdict(list))
        # cluster label -> vertex index -> vertex
        self.edgeVertexDict = defaultdict(dict)

        self._initialize()

    def _getVertexIfExists(self, vertexIndex, clusterLabel0, clusterLabel1, edgeIsCoast):
        """Gets the vertex at vertexIndex from edgeVertexDict, creating a new instance if it doesn't yet exist"""
        if vertexIndex in self.edgeVertexDict[clusterLabel0]:
            vertex = self.edgeVertexDict[clusterLabel0][vertexIndex]
            self.edgeVertexDict[clusterLabel1][vertexIndex] = vertex
        elif vertexIndex in self.edgeVertexDict[clusterLabel1]:
            vertex = self.edgeVertexDict[clusterLabel1][vertexIndex]
            self.edgeVertexDict[clusterLabel0][vertexIndex] = vertex
        else:
            vertex = Vertex(vertexIndex, self.vor.vertices[vertexIndex], edgeIsCoast)
            self.edgeVertexDict[clusterLabel0][vertexIndex] = vertex
            self.edgeVertexDict[clusterLabel1][vertexIndex] = vertex
        return vertex

    def _initialize(self):
        """
        Makes a dictionary mapping a cluster label to a dictionary mapping a vertex index to
        its two adjacent vertex indices for the cluster. Also creates a dictionary mapping
        cluster label to a dictionary mapping a vertex index to a vertex instance.
        """
        for i, pointIndices in enumerate(self.vor.ridge_points):
            clusterLabel0 = self._clusterLabels[pointIndices[0]]
            clusterLabel1 = self._clusterLabels[pointIndices[1]]
            if clusterLabel0 != clusterLabel1:
                edgeIsCoast = clusterLabel0 == self.waterLabel or clusterLabel1 == self.waterLabel
                vertexIndex0 = self.vor.ridge_vertices[i][0]
                vertexIndex1 = self.vor.ridge_vertices[i][1]

                # get vertices if they exist
                vertex0 = self._getVertexIfExists(vertexIndex0, clusterLabel0, clusterLabel1, edgeIsCoast)
                vertex1 = self._getVertexIfExists(vertexIndex1, clusterLabel0, clusterLabel1, edgeIsCoast)

                points = [self.points[pointIndex] for pointIndex in pointIndices]
                vertex0.addRegionPoints(points)
                vertex1.addRegionPoints(points)

                # add two vertices in edge to both clusters
                self.edgeRidgeDict[clusterLabel0][vertexIndex0].append(vertexIndex1)
                self.edgeRidgeDict[clusterLabel0][vertexIndex1].append(vertexIndex0)
                self.edgeRidgeDict[clusterLabel1][vertexIndex0].append(vertexIndex1)
                self.edgeRidgeDict[clusterLabel1][vertexIndex1].append(vertexIndex0)
