import math


class Vertex:
    # array for all the vertex objects, aligned with Voronoi's own
    vertex_arr = []
    # dict to hold indices of vertices for each cluster
    edge_vertex_dict = {}

    def __init__(self, x, y, idx, adj_idxs, region_idxs, region_group_labels):
        self.x = x
        self.y = y
        self.idx = idx
        self.adj_idxs = adj_idxs
        # these must match with region_group_labels
        self.region_idxs = region_idxs
        self.region_group_labels = region_group_labels

    def is_edge_vertex(self):
        """use for building edge vertex set for each group"""
        return len(set(self.region_group_labels)) > 1

    def _get_num_shared_region_labels(self, vertex, group_label):
        """
        Returns the number of shared regions of type group_label between
        this vertex and another vertex
         """
        num_in_common = 0
        for i in range(len(self.region_idxs)):
            for j in range(len(vertex.region_idxs)):
                if self.region_idxs[i] == vertex.region_idxs[j] \
                   and self.region_group_labels[i] == group_label:
                    num_in_common += 1
        return num_in_common

    def get_adj_edge_vert_idx(self, group_label, prev_vertex_idx):
        """used for getting the next vertex in the contiguous border"""
        candidates = []
        for idx in self.adj_idxs:
            if idx != prev_vertex_idx \
               and idx in self.edge_vertex_dict[group_label] \
                    and self._get_num_shared_region_labels(self.vertex_arr[idx],
                                                        group_label) == 1:
                return idx
        return None
