from collections import defaultdict


class InfectionNode:
    pass


class InfectionEdge:
    pass


class InfectionNetwork:
    """
    Keeps a record of all the infection paths
    """

    def __init__(self):
        # keep the paths in a dictionary
        # {(<class_name>, <class_name>, ...): <count>, ... }
        self.path_dict = defaultdict(int)

    def add_path(self, path, num=1):
        """
        Adds a path to the paths record
        :param path: The path to add
        :type path: tuple
        :param num: Number of this path to add
        :type num: int
        """
        self.path_dict[tuple(path)] += num

    def get_paths_counts(self):
        """
        Gets a list of all the paths that have been recorded with their counts
        :return: List of tuples (path, count). Paths are tuples of strings, counts are integers
        :rtype: list
        """
        return self.path_dict.items()
