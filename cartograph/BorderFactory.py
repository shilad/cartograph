from scipy.spatial import Voronoi
import numpy as np
from Vertex import Vertex
import Util
from collections import defaultdict

import Config
config = Config.BAD_GET_CONFIG()


class BorderFactory(object):

    water_label = 0
    points = []

    def __init__(self, x, y, cluster_labels):
        self.x = x
        self.y = y
        self.cluster_labels = cluster_labels
        BorderFactory.water_label = len(self.cluster_labels)-1

    @classmethod
    def from_file(cls, ):
        s = "." if debug else ""
        featureDict = Util.read_features(s + config.FILE_NAME_WATER_AND_ARTICLES,
                                         s + config.FILE_NAME_KEEP,
                                         s + config.FILE_NAME_WATER_CLUSTERS)
        idList = list(featureDict.keys())
        x, y, clusters = [], [], []
        for article in idList:
            if featureDict[article]["keep"] == "True":
                x.append(float(featureDict[article]["x"]))
                y.append(float(featureDict[article]["y"]))
                clusters.append(int(featureDict[article]["cluster"]))
        return cls(x, y, clusters)

    @staticmethod
    def _make_vertex_adjacency_list(vor):
        adj_lst = defaultdict(set)
        for ridge in vor.ridge_vertices:
            adj_lst[ridge[0]].add(ridge[1])
            adj_lst[ridge[1]].add(ridge[0])
        return adj_lst

    @staticmethod
    def _make_three_dicts(vor, cluster_labels):
        """
        Args:
            vor: The Voronoi object
            cluster_labels: A list of cluster labels for each input point (not vertex)

        Returns:
            Three dictionaries - the first maps each vertex index to a list of region indices that are adjacent to that
            vertex, the second maps vertex indices to a list of labels for each adjacent region, and the third maps
            a cluster label to all the vertex indices which touch a region of that label.
        """
        vert_reg_idxs_dict = defaultdict(list)
        vert_reg_labs_dict = defaultdict(list)
        group_vert_dict = defaultdict(set)
        for i, reg_idx in enumerate(vor.point_region):
            vert_idxs = vor.regions[reg_idx]
            label = cluster_labels[i]
            group_vert_dict[label].update(vert_idxs)
            for vert_idx in vert_idxs:
                vert_reg_idxs_dict[vert_idx].append(reg_idx)
                vert_reg_labs_dict[vert_idx].append(label)
        return vert_reg_idxs_dict, vert_reg_labs_dict, group_vert_dict

    @staticmethod
    def _make_vertex_array(vor, adj_lst, vert_reg_idxs_dict,
                           vert_reg_labs_dict):
        return [Vertex(v[0], v[1], i, adj_lst[i],
                vert_reg_idxs_dict[i], vert_reg_labs_dict[i])
                for i, v in enumerate(vor.vertices)]

    @staticmethod
    def _make_group_edge_vert_dict(vert_array, group_vert_dict):
        """maps group labels to edge vertex indices"""
        group_edge_vert_dict = defaultdict(set)
        for label in group_vert_dict:
            # can't do list comprehension because otherwise it's a generator later
            for vert_idx in group_vert_dict[label]:
                if vert_array[vert_idx].is_edge_vertex:
                    group_edge_vert_dict[label].add(vert_idx)
        return group_edge_vert_dict

    @staticmethod
    def _make_borders(vert_array, group_edge_vert_dict):
        """
        Internal function to build borders from generated data.
        Returns:
            A dictionary mapping labels to lists of lists of Vertex objects specifying each continent border
        """
        borders = defaultdict(list)
        for label in group_edge_vert_dict:
            while group_edge_vert_dict[label]:
                continent = []
                vert_idx = next(iter(group_edge_vert_dict[label]))
                while vert_idx is not None:
                    vert = vert_array[vert_idx]
                    continent.append(vert)
                    group_edge_vert_dict[label].remove(vert_idx)
                    vert_idx = vert.get_adj_edge_vert_idx(label, vert_idx)
                if len(continent) > config.MIN_NUM_IN_CONTINENT:
                    borders[label].append(continent)
        return _NaturalBorderMaker(borders).make_borders_natural()

    def build(self):
        """
        Returns:
            a dictionary mapping group labels to a list of list of tuples representing
            the different continents in each cluster
        """
        points = list(zip(self.x, self.y))
        BorderFactory.points = points
        vor = Voronoi(points)
        adj_lst = self._make_vertex_adjacency_list(vor)
        vert_reg_idxs_dict, vert_reg_labs_dict, group_vert_dict = self._make_three_dicts(vor, self.cluster_labels)
        vert_array = self._make_vertex_array(vor, adj_lst, vert_reg_idxs_dict,
                                             vert_reg_labs_dict)
        Vertex.vertex_arr = vert_array
        group_edge_vert_dict = self._make_group_edge_vert_dict(vert_array,
                                                               group_vert_dict)
        Vertex.edge_vertex_dict = group_edge_vert_dict

        return self._make_borders(vert_array, group_edge_vert_dict)


class _NaturalBorderMaker:

    def __init__(self, borders):
        self.borders = borders

    @staticmethod
    def _wrap_range(start, stop, length, reverse=False):
        """
        Returns:
            range from start to stop *inclusively* modulo length
        """
        start %= length
        stop %= length
        if reverse:
            if stop >= start:
                return range(start, -1, -1) + range(length - 1, stop - 1, -1)
            else:
                return range(start, stop - 1, -1)
        else:
            if start >= stop:
                return range(start, length) + range(0, stop + 1)
            else:
                return range(start, stop + 1)

    @staticmethod
    def _blur(array, circular, radius):
        # arrays which are shorter than this will be blurred to a single point
        if len(array) <= radius * 2 + 1:
            return array
        blurred = []
        if circular:
            for i, _ in enumerate(array):
                start = i - radius
                stop = i + radius
                neighborhood = [
                    array[j] for j in _NaturalBorderMaker._wrap_range(start, stop, len(array))]
                blurred.append(np.average(neighborhood))
        else:
            for i, _ in enumerate(array):
                start = max(0, i - radius)
                stop = min(len(array) - 1, i + radius)
                neighborhood = [array[j] for j in range(start, stop + 1)]
                blurred.append(np.average(neighborhood))
        return blurred

    @staticmethod
    def _process_vertices(vertices, circular):
        """
        Processes the list of vertices based on whether they are part of a coast or not
        Args:
            vertices: list of Vertex objects
            circular: whether or not the list forms a circular border

        Returns:
            A list of tuples for each point in the new border
        """
        if len(vertices) < 2:
            return vertices
        if vertices[0].is_edge_coast(vertices[1], BorderFactory.water_label):
            x, y = [], []
            for i in range(len(vertices)-1):
                x, y = _NoisyEdgesMaker()
        else:
            x = [vertex.x for vertex in vertices]
            y = [vertex.y for vertex in vertices]
            x = _NaturalBorderMaker._blur(x, circular, config.BLUR_RADIUS)
            y = _NaturalBorderMaker._blur(y, circular, config.BLUR_RADIUS)
        return zip(x, y)

    @staticmethod
    def _get_consensus_border_intersection(indices1, indices2, len1, len2, reversed2):
        """
        Args:
            indices1: *aligned* indices of points in points1 which are in intersection
            indices2: *aligned* indices of points in points2 which are in intersection
            len1: length of points1
            len2: length of points2
            reversed2: Whether or not indices2 is in reversed order
        Returns:
            list of lists of contiguous regions
        """
        if len(indices1) != len(indices2):
            raise ValueError("Lists of indices must be the same length.")

        # build list for each contiguous region
        diff2 = -1 if reversed2 else 1
        consensus_lists = [[(indices1[0], indices2[0])]]
        for i in range(1, len(indices1)):
            prev = consensus_lists[-1][-1]
            current = (indices1[i], indices2[i])
            if (prev[0] + 1) % len1 == current[0] and \
                    (prev[1] + diff2) % len2 == current[1]:
                consensus_lists[-1].append(current)
            else:
                consensus_lists.append([current])

        # check for circular and index 0 in the middle of an intersection
        first = consensus_lists[0][0]
        last = consensus_lists[-1][-1]
        if (last[0] + 1) % len1 == first[0] and \
                (last[1] + diff2) % len2 == first[1]:
            if len(consensus_lists) == 1:
                # it's circular
                return consensus_lists, True
            else:
                # 0 is in middle of intersection
                consensus_lists[0] = consensus_lists[-1] + consensus_lists[0]
                consensus_lists.pop()
        return consensus_lists, False

    @staticmethod
    def _get_border_region_indices(points, intersection):
        """
        Returns:
            list of indices of points in points which are in intersection
        """
        indices = []
        for i, point in enumerate(points):
            if point in intersection:
                indices.append(i)
        return indices

    @staticmethod
    def _get_intersecting_borders(points1, points2):
        """
        Returns:
            list of lists of tuples which represents the aligned indices of points1 and points2 in each contiguous
            intersection of points1 and points2 and whether the intersection is circular.
            Ex: [[(pt1_0, pt2_0), (pt1_1, pt2_1), ...], [...]]
        """
        points1_set = set(points1)
        points2_set = set(points2)
        intersection = points1_set & points2_set
        if intersection:
            points1_border_idxs = _NaturalBorderMaker._get_border_region_indices(points1, intersection)
            points2_border_idxs = _NaturalBorderMaker._get_border_region_indices(points2, intersection)

            # align lists, taking orientation into account
            search_point = points1[points1_border_idxs[0]]
            offset = 0
            for i, index in enumerate(points2_border_idxs):
                if search_point == points2[index]:
                    offset = i
                    break
            # check for direction
            reverse = False
            if len(points1_border_idxs) > 1:
                try_index = (offset + 1) % len(points2_border_idxs)
                if points2[points2_border_idxs[try_index]] != points1[points1_border_idxs[1]]:
                    reverse = True
            if reverse:
                # gnarly bug this one was
                # reversing the list means offsetting by one extra - set the new 0 pos at the end of the list
                # before reversing
                points2_border_idxs = np.roll(points2_border_idxs, -offset - 1)
                points2_border_idxs = list(reversed(points2_border_idxs))
            else:
                points2_border_idxs = np.roll(points2_border_idxs, -offset)

            return _NaturalBorderMaker._get_consensus_border_intersection(
                points1_border_idxs, points2_border_idxs, len(points1), len(points2), reverse
            )
        return [], False

    @staticmethod
    def _replace_into_border(region, replace, start, stop):
        """
        Inserts replace between start and stop (counted inclusively) into the list region
        """
        if stop < start:
            region = region[:start]
            region[:stop+1] = replace
        else:
            region[start:stop+1] = replace
        return region

    @staticmethod
    def _make_new_regions(region1, region2):
        """
        Args:
            region1: One region represented by Vertex objects
            region2: Another region represented by Vertex objects
        Returns:
            region1 and region2 with their intersecting points modified
        """
        points1 = [(vertex.x, vertex.y) for vertex in region1]
        points2 = [(vertex.x, vertex.y) for vertex in region2]
        consensus_lists, circular = _NaturalBorderMaker._get_intersecting_borders(points1, points2)
        processed = []
        for contiguous in consensus_lists:
            # sanity check
            for indices in contiguous:
                assert points1[indices[0]] == points2[indices[1]]
            indices = zip(*contiguous)  # make separate lists for region1 and region2 coordinates
            processed.append(
                _NaturalBorderMaker._process_vertices([region1[i] for i in indices[0]], circular)
            )
        for i, contiguous in enumerate(processed):
            start = consensus_lists[i][0][0]
            stop = consensus_lists[i][-1][0]
            _NaturalBorderMaker._replace_into_border(region1, contiguous, start, stop)
            start = consensus_lists[i][0][1]
            stop = consensus_lists[i][-1][1]
            _NaturalBorderMaker._replace_into_border(region2, contiguous, start, stop)
        return region1, region2

    @staticmethod
    def _make_region_adj_matrix_and_index_key(borders):
        """
        Returns:
            an adjacency matrix and a dictionary mapping group labels to indices
            (i.e., adj_matrix[index_key[group_label] + region_index]
        """
        index_key = {}
        n = 0
        for label in range(len(borders)):
            index_key[label] = n
            n += len(borders[label])
        return np.zeros((n, n), dtype=np.int8), index_key

    def make_borders_natural(self):
        """
        Returns:
            the borders object where the intersecting borders are made more natural
        """
        adj_matrix, index_key = _NaturalBorderMaker._make_region_adj_matrix_and_index_key(self.borders)
        for group_label in self.borders:
            for reg_idx, region in enumerate(self.borders[group_label]):
                reg_adj_idx = index_key[group_label] + reg_idx
                for search_group_label in self.borders:
                    if group_label is not search_group_label:
                        for search_reg_idx, search_region in enumerate(self.borders[search_group_label]):
                            search_reg_adj_idx = index_key[search_group_label] + search_reg_idx
                            if not adj_matrix[reg_adj_idx][search_reg_adj_idx]:
                                self.borders[group_label][reg_idx], \
                                    self.borders[search_group_label][search_reg_idx] = \
                                    _NaturalBorderMaker._make_new_regions(region, search_region)
                                adj_matrix[reg_adj_idx][search_reg_adj_idx] = 1
                                adj_matrix[search_reg_adj_idx][reg_adj_idx] = 1
        # remove water points
        del self.borders[len(self.borders)-1]
        return self.borders


class _NoisyEdgesMaker:
    """
    Implementation based on https://github.com/amitp/mapgen2/blob/master/NoisyEdges.as
    """

    def __init__(self, pt0, pt1, pt2, pt3):
        self.pt0 = pt0
        self.pt1 = pt1
        self.pt2 = pt2
        self.pt3 = pt3
        self.midpoint = self._interpolate(pt0, pt2)
        self.min_length = 0.01

    @staticmethod
    def _interpolate(pt0, pt1, value=0.5):
        return pt0 + (np.subtract(pt1, pt0) * value)

    def _subdivide(self, a, b, c, d):
        pass

    def _make_half_noisy_edge(self, a, b, c, d):
        edge = [a]
        self._subdivide(a, b, c, d)
        edge.append(c)
        return edge

    def make_noisy_edge(self):
        mid0 = self._interpolate(self.pt0, self.pt1)
        mid1 = self._interpolate(self.pt1, self.pt2)
        mid2 = self._interpolate(self.pt2, self.pt3)
        mid3 = self._interpolate(self.pt3, self.pt0)
        return self._make_half_noisy_edge(self.pt0, mid0, self.midpoint, mid3) + \
               self._make_half_noisy_edge(self.midpoint, mid1, self.pt2, mid2)

debug = False

if __name__ == '__main__':
    debug = True
    BorderFactory.from_file().build()
