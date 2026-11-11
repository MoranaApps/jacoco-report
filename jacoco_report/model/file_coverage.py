"""
A module that contains the FileCoverage class
"""

from dataclasses import dataclass

from jacoco_report.model.coverage import Coverage


@dataclass
class _FileLocation:
    """
    The location fields of a FileCoverage: file_name, file_path
    """

    file_name: str
    file_path: str


# dataclasses collect fields in reverse MRO order, so listing _FileLocation after Coverage
# puts file_name and file_path before the six counters, keeping the positional order of the
# original __init__.
@dataclass
class FileCoverage(Coverage, _FileLocation):
    """
    A class that represents the coverage of a file
    """

    def __str__(self):
        """
        Returns the string representation of the FileCoverage class

        Returns:
            str: The string representation of the FileCoverage class
        """
        return f"File: {self.file_name}, Path: {self.file_path}, {super().__str__()}"
