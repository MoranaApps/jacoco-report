"""
A module that contains the class that represents a module in a project.
"""


# pylint: disable=too-few-public-methods
class Module:
    """
    A class that represents a module in a project.
    """

    def __init__(self, name: str, unique_path: str, min_coverage_overall: float, min_coverage_changed_files: float,
                 min_coverage_changed_per_file: float):
        """
        Constructor of the class.

        Parameters:
            name (str): The name of the module.
            unique_path (str): The root path of the module.
            min_coverage_overall (float): The minimum coverage that the module should have.
            min_coverage_changed_files (float): The minimum coverage that the module should have in the changed files.
            min_coverage_changed_per_file (float): The minimum coverage that the module should have in the changed files per file.
        """
        self.name = name
        self.root_path = unique_path
        self.min_coverage_overall = min_coverage_overall
        self.min_coverage_changed_files = min_coverage_changed_files
        self.min_coverage_per_changed_file = min_coverage_changed_per_file
