VoronoiWrapper.py:
Defines the class VoronoiWrapper.

The init method creates a few class variables including a set of points defined by
the x and y inputs as well as the cluster and water labels that are also based on the inputs to the constructor which
represents the voronoi cluster. Additionally, this method creates edgeRidgeDict and edgeVertexDict. edgeRidgeDict is
a dictionary of dictionaries, in which the first key is a cluster label and the second key is the vertex and its values
are adjacent vertices. The next dictionary of dictionaries created is the edgeVertexDict which takes in a cluster label
and then for the second key it takes in the vertex ID and returns the vertex value (assumedly the x and y coordinates
along with some other stuff). And then it calls initialize (which is a method described below).

The getVertexIfExists method gets the vertex at vertexIndex from edgeVertexDict, creating a new instance if it doesn't
exist yet. If a vertex is in the first cluster, we set vertex to be the information returned by edgeVertexDict, and then
we add the vertex to the second cluster, and vice versa (if it is in the second cluster. If the vertex doesn't exist,
then we create a vertex with the boolean value edgeIsCoast, and then both clusters clusterLabel0 and clusterLabel1 get
that vertex added to their edgeVertexDictionaries. This means that border points are in both clusters and vertices
can be shared by multiple clusters if need be. Finally, we return the vertex.

The initialize method makes a dictionary mapping a cluster label to a dictionary mapping a vertex index to
its two adjacent vertex indices for the cluster. It also creates a dictionary mapping cluster label to a dictionary
mapping a vertex index to a vertex instance. We think this is used to create more jagged lines.

BorderProcessor.py:
Defines the class BorderProcessor, which is responsible for processing borders made by BorderBuilder by blurring
the borders and modifying vertices.

The init method sets up the class variables borders, blurRadius, minBoredNoiseLength, waterLabel, and noise.

The blur method takes in an array (which I think is either an array of the x locs of vertices or the y locs of
vertices). It sets blurred to an empty array. If circular, it loops over the array and sets the neighborhood to
be array values with indices within the start, stop range defined by i-radius, i+radius. It then appends the average
of the neighborhood to blurred. Otherwise, it loops over the array and sets the neighborhood to be array values with
indices within the start, stop range defined by max(0, i-radius), min(len(array) -1, i+radius). It then appends the
average to blurred.

The processVertices method processes the list of vertices based on whether they are part of a coast or not
and returns a list of modified vertices (that can be longer than input).

BorderBuilder.py:
Defines the class BorderBuilder, which is responsible for creating borders.

The init method creates class variables (x, y, clusterLabels, minNumInCluster, blurRadius, minBorderNoiseLength,
initialize).

The initialize method the featureDict is first populated with the sample data if there are sample borders in the config
file. If there isn't sample data to get populating data from, then the init function takes in the normal data from the
config file using the config.get function in order to populate thefeatureDict. Then x,y is populated.

The build method first initializes borders to a dictionary of lists and waterLabel to the max cluster label. It then
creates the voronoi tessellation. Next, for each cluster label in edgeRidgeDict, it sets edgeRidgeDict to a dict where
the key is a vertex and its values are its two adjacent vertices. It also sets edgeVertexDict to a dict where the key
is a vertex ID and its value is information (assumedly the x and y coordinates along with some other stuff). Next,
it loops over edgeVertexDict and populates the continent. Then, it calls Borderprocesser and removes water points.
Finally, it loops over the continents and adds x,y coordinates.

BorderFactoryTest.py:
Tests BorderProcesser. test_makeNewRegionFromProcessed tests the makeNewRegionFromProcessed method in BorderProcessor,
by using different assertEquals tests. These tests are used to make it easier to detect where something is going wrong.

Noiser.py:
Defines the class NoisyEdgesMaker, which replaces the polygon borders with a noisy line, so the borders look more
realistic. Returns a new set of points that defines the noised lines.
(At the moment, this process is v self contained)

Vertex.py:
Defines the class vertex, which has the information of the vertex, like its index, x, y coords, whether or not it is
on the coast and regionPoints, which is populated in addRegionPoints.
Note-- we don't know what regionPoints is or how exactly update (in the addRegionPoints method) works.