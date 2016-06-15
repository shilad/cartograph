import math
import Constants


class Vertex:
    # array for all the vertex objects, aligned with Voronoi's own
    vertex_arr = []
    # dict to hold indices of vertices for each cluster
    edge_vertex_dict = {}

    def __init__(self, x, y, idx, adj_idxs, region_idxs, region_group_labels, is_region_large):
        self.x = x
        self.y = y
        self.idx = idx
        self.adj_idxs = adj_idxs
        # these must match with region_group_labels
        self.region_idxs = region_idxs
        self.region_group_labels = region_group_labels
        self.is_region_large = is_region_large

    def _calc_distance(self, vertex):
        if vertex.idx == -1:
            return float("inf")
        return math.hypot(self.x - vertex.x, self.y - vertex.y)

    def is_edge_vertex(self):
        """use for building edge vertex set for each group"""
        num_close = 0
        for idx in self.adj_idxs:
            if self._calc_distance(self.vertex_arr[idx]) <= Constants.SEARCH_RADIUS:
                num_close += 1
        if num_close >= 2:
            if len(set(self.adj_idxs)) > 1:
                return True
            num_large_regions = 0
            for region_idx in self.region_idxs:
                if self.is_region_large[region_idx]:
                    num_large_regions += 1
            return num_large_regions == 1 or num_large_regions == 2

    def _get_num_valid_shared_region_labels(self, vertex, group_label):
        """
        Returns the number of shared regions of this vertex's group between this vertex
        and another vertex with the exception that a shared region is only counted if it
        is small (in order to allow coasts to form)
         """
        num_in_common = 0
        for i in range(len(self.region_idxs)):
            for j in range(len(vertex.region_idxs)):
                if self.region_idxs[i] == vertex.region_idxs[j] \
                   and self.region_group_labels[i] == group_label \
                        and not self.is_region_large[self.region_idxs[i]]:
                    num_in_common += 1
        return num_in_common

    def get_adj_edge_vert_idx(self, group_label, prev_vertex_idx):
        """use for getting the next vertex in the contiguous border"""
        candidates = []
        for idx in self.adj_idxs:
            if idx != prev_vertex_idx \
               and idx in self.edge_vertex_dict[group_label]:
                candidates.append(idx)
        for idx in candidates:
            if self._get_num_valid_shared_region_labels(self.vertex_arr[idx],
                                                        group_label) == 1:
                return idx
        return None
