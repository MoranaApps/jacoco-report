"""
A module that contains the FileCoverage class
"""

from jacoco_report.model.counter import Counter
from jacoco_report.model.coverage import Coverage


# pylint: disable=too-few-public-methods
class FileCoverage(Coverage):
    """
    A class that represents the coverage of a file
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        file_name: str,
        file_path: str,
        instruction: Counter,
        branch: Counter,
        line: Counter,
        complexity: Counter,
        method: Counter,
        clazz: Counter,
    ):
        """
        A constructor for the FileCoverage class

        Parameters:
            file_name (str): The name of the file
            file_path (str): The path of the file
            instruction (Counter): The instruction counter
            branch (Counter): The branch counter
            line (Counter): The line counter
            complexity (Counter): The complexity counter
            method (Counter): The method counter
            clazz (Counter): The class counter
        """
        super().__init__(instruction, branch, line, complexity, method, clazz)
        self.file_name = file_name
        self.file_path = file_path

    def __str__(self):
        """
        Returns the string representation of the FileCoverage class

        Returns:
            str: The string representation of the FileCoverage class
        """
        return f"File: {self.file_name}, Path: {self.file_path}, {super().__str__()}"
