from scipy.spatial import Voronoi
from collections import defaultdict
from _Vertex import Vertex


class VoronoiWrapper:

    def __init__(self, x, y, clusterLabels):
        points = zip(x, y)
        self._clusterLabels = clusterLabels
        self.waterLabel = max(clusterLabels)
        self.vor = Voronoi(points)

        self.edgeRidgeDict = defaultdict(lambda: defaultdict(list))
        self.edgeVertexDict = defaultdict(dict)

        self._initialize()

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
                # tuple containing index and point
                vertex0 = Vertex(vertexIndex0, self.vor.vertices[vertexIndex0], edgeIsCoast)
                vertex1 = Vertex(vertexIndex1, self.vor.vertices[vertexIndex1], edgeIsCoast)
                vertex0.addPointIndices(pointIndices)
                vertex1.addPointIndices(pointIndices)

                # add two points in edge to both clusters
                self.edgeRidgeDict[clusterLabel0][vertexIndex0].append(vertexIndex1)
                self.edgeRidgeDict[clusterLabel0][vertexIndex1].append(vertexIndex0)
                self.edgeRidgeDict[clusterLabel1][vertexIndex0].append(vertexIndex1)
                self.edgeRidgeDict[clusterLabel1][vertexIndex1].append(vertexIndex0)

                # add vertices to dictionaries for both clusters
                self.edgeVertexDict[clusterLabel0][vertexIndex0] = vertex0
                self.edgeVertexDict[clusterLabel0][vertexIndex1] = vertex1
                self.edgeVertexDict[clusterLabel1][vertexIndex0] = vertex0
                self.edgeVertexDict[clusterLabel1][vertexIndex1] = vertex1