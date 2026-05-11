"""
A module that contains the ReportGroup class.
"""

from typing import Optional


class ReportGroup:
    """
    A class that represents a report group — a named set of JaCoCo report paths
    with optional per-group thresholds and baseline paths.
    """

    def __init__(
        self,
        name: str,
        paths: list[str],
        min_coverage_overall: Optional[float] = None,
        min_coverage_changed_files: Optional[float] = None,
        min_coverage_per_changed_file: Optional[float] = None,
        baseline_paths: Optional[list[str]] = None,
    ):
        self.name = name
        self.paths = paths
        self.min_coverage_overall = min_coverage_overall
        self.min_coverage_changed_files = min_coverage_changed_files
        self.min_coverage_per_changed_file = min_coverage_per_changed_file
        self.baseline_paths = baseline_paths
