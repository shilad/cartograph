from scipy.spatial import Voronoi
from Vertex import Vertex
import Util

import Config
config = Config.BAD_GET_CONFIG()


class BorderFactory(object):

    def __init__(self, x, y, cluster_labels):
        self.x = x
        self.y = y
        self.cluster_labels = cluster_labels

    @classmethod
    def from_file(cls, ):
        featureDict = Util.read_features(config.FILE_NAME_WATER_AND_ARTICLES,
                                         config.FILE_NAME_KEEP,
                                         config.FILE_NAME_WATER_CLUSTERS)
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
        adj_lst = {vert_idx: set() for vert_idx in range(len(vor.vertices))}
        adj_lst[-1] = set()
        for ridge in vor.ridge_vertices:
            adj_lst[ridge[0]].add(ridge[1])
            adj_lst[ridge[1]].add(ridge[0])
        return adj_lst

    @staticmethod
    def _make_three_dicts(vor, cluster_labels):
        vert_reg_idxs_dict = {vert_idx: []
                              for vert_idx in range(len(vor.vertices))}
        vert_reg_idxs_dict[-1] = []
        vert_reg_labs_dict = {vert_idx: []
                              for vert_idx in range(len(vor.vertices))}
        vert_reg_labs_dict[-1] = []
        group_vert_dict = {}
        for label in set(cluster_labels):
            group_vert_dict[label] = set()
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
        vert_arr = []
        for i, v in enumerate(vor.vertices):
            vert_arr.append(Vertex(v[0], v[1], i, adj_lst[i],
                            vert_reg_idxs_dict[i], vert_reg_labs_dict[i]))
        return vert_arr

    @staticmethod
    def _make_group_edge_vert_dict(vert_array, group_vert_dict):
        """maps group labels to edge vertex indices"""
        group_edge_vert_dict = {}
        for label in group_vert_dict:
            edge_verts = set()
            # v is an index to Voronoi vertices
            for vert_idx in group_vert_dict[label]:
                if vert_array[vert_idx].is_edge_vertex():
                    edge_verts.add(vert_idx)
            group_edge_vert_dict[label] = edge_verts
        return group_edge_vert_dict

    @staticmethod
    def _make_borders_natural(borders):
        # TODO: implement this
        return borders

    def _make_borders(self, vert_array, group_edge_vert_dict):
        """internal function to build borders from generated data"""
        borders = {}
        del group_edge_vert_dict[len(group_edge_vert_dict) - 1]
        for label in group_edge_vert_dict:
            borders[label] = []
            while group_edge_vert_dict[label]:
                cluster_border = []
                vert_idx = next(iter(group_edge_vert_dict[label]))
                while vert_idx is not None:
                    vert = vert_array[vert_idx]
                    cluster_border.append((vert.x, vert.y))
                    group_edge_vert_dict[label].discard(vert_idx)
                    vert_idx = vert.get_adj_edge_vert_idx(label, vert_idx)
                if len(cluster_border) > config.MIN_NUM_IN_CLUSTER:
                    borders[label].append(cluster_border)
        return BorderFactory._make_borders_natural(borders)

    def build(self):
        """makes a dictionary mapping group labels to an array of array of
            tuples representing the different clusters in the each group"""
        points = list(zip(self.x, self.y))
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

if __name__ == '__main__':
    BorderFactory.from_file().build()
