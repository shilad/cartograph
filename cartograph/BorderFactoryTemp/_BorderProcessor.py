import numpy as np
from cartograph import Config
config = Config.BAD_GET_CONFIG()


class BorderProcessor:

        def __init__(self, borders):
            self.borders = borders

        @staticmethod
        def _wrap_range(start, stop, length, reverse=False):
            """
            Return:
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
        def _blur(array, circular):
            blurred = []
            if circular:
                for i, _ in enumerate(array):
                    start = i - config.BLUR_RADIUS
                    stop = i + config.BLUR_RADIUS
                    neighborhood = [
                        array[j] for j in BorderProcessor._wrap_range(start, stop, len(array))]
                    blurred.append(np.average(neighborhood))
            else:
                for i, _ in enumerate(array):
                    start = max(0, i - config.BLUR_RADIUS)
                    stop = min(len(array) - 1, i + config.BLUR_RADIUS)
                    neighborhood = [array[j] for j in range(start, stop + 1)]
                    blurred.append(np.average(neighborhood))
            return blurred

        @staticmethod
        def _blur_points(points, circular):
            unzipped = zip(*points)
            x = BorderProcessor._blur(unzipped[0], circular)
            y = BorderProcessor._blur(unzipped[1], circular)
            return zip(x, y)

        @staticmethod
        def _get_consensus_border_intersection(indices1, indices2, len1, len2, reversed2):
            """
            Args:
                indices1: *aligned* indices of points in region1 which are in intersection
                indices2: *aligned* indices of points in region2 which are in intersection
                len1: length of region1
                len2: length of region2
                reversed2: Whether or not indices2 is in reversed order
            Returns:
                list of lists of contiguous regions
            """
            assert len(indices1) == len(indices2)
            consensus_lists = []
            diff2 = -1 if reversed2 else 1
            n = len(indices1)
            i = 0
            # build list for each contiguous region
            while i < n:
                current = (indices1[i], indices2[i])
                next_ = (indices1[(i + 1) % n], indices2[(i + 1) % n])
                contiguous = [current]
                while (current[0] + 1) % len1 == next_[0] and \
                        (current[1] + diff2) % len2 == next_[1] and i < n:
                    i += 1
                    contiguous.append(next_)
                    current = next_
                    next_ = (indices1[(i + 1) % n], indices2[(i + 1) % n])
                consensus_lists.append(contiguous)
                i += 1

            # check for circular and index 0 in the middle of an intersection
            first = consensus_lists[0][0]
            last = consensus_lists[-1][-1]
            if (last[0] + 1) % len1 == first[0] and \
                    (last[1] + diff2) % len2 == first[1]:
                # TODO: this never actually runs (with current data)
                if len(consensus_lists) == 1:
                    # it's circular
                    return consensus_lists, True
                else:
                    # 0 is in middle of intersection
                    consensus_lists[0] = consensus_lists[-1] + consensus_lists[0]
                    consensus_lists.pop()
            return consensus_lists, False

        @staticmethod
        def _get_border_region_indices(region, intersection):
            """
            Returns:
                list of indices of points in region which are in intersection
            """
            indices = []
            for i, point in enumerate(region):
                if region[i] in intersection:
                    indices.append(i)
            return indices

        @staticmethod
        def _get_intersecting_borders(region1, region2):
            """
            Returns:
                list of lists of tuples which represents the aligned indices of region1 and region2 in each contiguous
                intersection of region1 and region2 and whether the intersection is circular.
                Ex: [[(pt1_0, pt2_0), (pt1_1, pt2_1), ...], [...]]
            """
            region1_set = set(region1)
            region2_set = set(region2)
            intersection = region1_set & region2_set
            if intersection:
                region1_border_idxs = BorderProcessor._get_border_region_indices(region1, intersection)
                region2_border_idxs = BorderProcessor._get_border_region_indices(region2, intersection)

                # align lists, taking orientation into account
                search_point = region1[region1_border_idxs[0]]
                offset = 0
                for i, index in enumerate(region2_border_idxs):
                    if search_point == region2[index]:
                        offset = i
                        break
                # check for direction
                reverse = False
                if len(region1_border_idxs) > 1:
                    try_index = (offset + 1) % len(region2_border_idxs)
                    if region2[region2_border_idxs[try_index]] != region1[region1_border_idxs[1]]:
                        reverse = True
                if reverse:
                    # gnarly bug this one was
                    # reversing the list means offsetting by one extra - set the new 0 pos at the end
                    region2_border_idxs = np.roll(region2_border_idxs, -offset - 1)
                    region2_border_idxs = list(reversed(region2_border_idxs))
                else:
                    region2_border_idxs = np.roll(region2_border_idxs, -offset)

                return BorderProcessor._get_consensus_border_intersection(
                    region1_border_idxs, region2_border_idxs, len(region1), len(region2), reverse
                )
            return [], False

        @staticmethod
        def _make_new_regions(region1, region2):
            """
            Returns:
                region1 and region2 with their intersecting points modified
            """
            consensus_lists, circular = BorderProcessor._get_intersecting_borders(region1, region2)
            processed = []
            for contiguous in consensus_lists:
                # sanity check
                for indices in contiguous:
                    assert region1[indices[0]] == region2[indices[1]]
                indices = zip(*contiguous)  # make separate lists for region1 and region2 coordinates
                processed.append(
                    BorderProcessor._blur_points([region1[i] for i in indices[0]], circular)
                )
            for i, contiguous in enumerate(processed):
                for j, point in enumerate(contiguous):
                    reg1_idx = consensus_lists[i][j][0]
                    reg2_idx = consensus_lists[i][j][1]
                    region1[reg1_idx] = point
                    region2[reg2_idx] = point
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

        def process(self):
            """
            Returns:
                the borders object where the intersecting borders are made more natural
            """
            adj_matrix, index_key = BorderProcessor._make_region_adj_matrix_and_index_key(self.borders)
            for group_label in self.borders.keys():
                for reg_idx, region in enumerate(self.borders[group_label]):
                    reg_adj_idx = index_key[group_label] + reg_idx
                    for search_group_label in self.borders.keys():
                        if group_label is not search_group_label:
                            for search_reg_idx, search_region in enumerate(self.borders[search_group_label]):
                                search_reg_adj_idx = index_key[search_group_label] + search_reg_idx
                                if not adj_matrix[reg_adj_idx][search_reg_adj_idx]:
                                    self.borders[group_label][reg_idx], \
                                        self.borders[search_group_label][search_reg_idx] = \
                                        BorderProcessor._make_new_regions(region, search_region)
                                    adj_matrix[reg_adj_idx][search_reg_adj_idx] = 1
                                    adj_matrix[search_reg_adj_idx][reg_adj_idx] = 1