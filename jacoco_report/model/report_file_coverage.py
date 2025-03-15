"""
This module contains the ReportFileCoverage class
"""

from typing import Optional

from jacoco_report.model.coverage import Coverage
from jacoco_report.model.file_coverage import FileCoverage


# pylint: disable=too-few-public-methods
class ReportFileCoverage:
    """
    A class that represents the coverage of a report file.
    Class variables are filled with data from the XML report file.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        path: str,
        name: str,
        overall_coverage: Coverage,
        changed_files_coverage: dict[str, FileCoverage],
        module_name: Optional[str] = None,
    ):
        """
        A constructor for the CoverageReport class

        Parameters:
            path (str): The path of the coverage report
            overall_coverage (Coverage): The overall coverage
            changed_files_coverage (dict[str, FileCoverage]): The coverage of the changed files
            module_name (str): The name of the module

        Returns:
            None
        """
        self.path = path
        self.name = name

        # Represents the module name of the report file.
        if module_name is not None:
            self.module_name: str = module_name
        else:
            self.module_name: str = "Unknown"

        # Represents the overall coverage of the report file.
        self.overall_coverage: Coverage = overall_coverage

        # Represents the coverage of the changed files only.
        # Does not include all files in the report.
        self.changed_files_coverage: dict[str, FileCoverage] = changed_files_coverage
