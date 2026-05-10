"""
This module contains the ReportFileCoverage class
"""

from typing import Optional

from jacoco_report.model.coverage import Coverage
from jacoco_report.model.file_coverage import FileCoverage


class ReportFileCoverage:
    """
    A class that represents the coverage of a report file.
    Class variables are filled with data from the XML report file.
    """

    def __init__(
        self,
        path: str,
        name: str,
        overall_coverage: Coverage,
        changed_files_coverage: dict[str, FileCoverage],
        group_name: Optional[str] = None,
    ):
        self.path = path
        self.name = name
        self.group_name: str = group_name if group_name else "Unknown"

        # Represents the overall coverage of the report file.
        self.overall_coverage: Coverage = overall_coverage

        # Represents the coverage of the changed files only.
        # Does not include all files in the report.
        self.changed_files_coverage: dict[str, FileCoverage] = changed_files_coverage
