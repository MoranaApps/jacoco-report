"""
A module that contains the EvaluatedCoverage class.
"""

from jacoco_report.model.counter import Counter


class EvaluatedReportCoverage:
    """
    A class that represents an evaluated coverage of one report file or report group.
    """

    def __init__(self, name: str = "Unknown", group_name: str = "Unknown", path: str = ""):
        self.name: str = name
        self.path: str = path
        self.group_name: str = group_name

        # PR comment data
        # summary data
        self.overall_passed: bool = True
        self.overall_coverage_reached: float = 0.0
        self.overall_coverage_threshold: float = 0.0
        self.overall_coverage: Counter = Counter(0, 0)  # to keep information about coverage weight

        self.avg_changed_files_passed: bool = True
        self.avg_changed_files_coverage_reached: float = 0.0
        self.avg_changed_files_coverage: Counter = Counter(0, 0)  # to keep information about coverage weight

        # per each changed file data
        self.changed_files_passed: dict[str, bool] = {}
        self.changed_files_threshold: float = 0.0
        self.changed_files_coverage_reached: dict[str, float] = {}

        self.per_changed_file_threshold: float = 0.0

    def to_dict(self) -> dict:
        """Convert object to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "path": self.path,
            "group_name": self.group_name,
            "overall_passed": self.overall_passed,
            "overall_coverage_reached": self.overall_coverage_reached,
            "overall_coverage_threshold": self.overall_coverage_threshold,
            "overall_coverage": {"missed": self.overall_coverage.missed, "covered": self.overall_coverage.covered},
            "avg_changed_files_passed": self.avg_changed_files_passed,
            "avg_changed_files_coverage_reached": self.avg_changed_files_coverage_reached,
            "avg_changed_files_coverage": {
                "missed": self.avg_changed_files_coverage.missed,
                "covered": self.avg_changed_files_coverage.covered,
            },
            "changed_files_passed": self.changed_files_passed,
            "changed_files_threshold": self.changed_files_threshold,
            "changed_files_coverage_reached": self.changed_files_coverage_reached,
            "per_changed_file_threshold": self.per_changed_file_threshold,
        }

    def clone(self) -> "EvaluatedReportCoverage":
        """Return a detached copy of the evaluated coverage object."""
        clone = EvaluatedReportCoverage(self.name, self.group_name, self.path)
        clone.overall_passed = self.overall_passed
        clone.overall_coverage_reached = self.overall_coverage_reached
        clone.overall_coverage_threshold = self.overall_coverage_threshold
        clone.overall_coverage = Counter(self.overall_coverage.missed, self.overall_coverage.covered)

        clone.avg_changed_files_passed = self.avg_changed_files_passed
        clone.avg_changed_files_coverage_reached = self.avg_changed_files_coverage_reached
        clone.avg_changed_files_coverage = Counter(
            self.avg_changed_files_coverage.missed,
            self.avg_changed_files_coverage.covered,
        )

        clone.changed_files_passed = dict(self.changed_files_passed)
        clone.changed_files_threshold = self.changed_files_threshold
        clone.changed_files_coverage_reached = dict(self.changed_files_coverage_reached)
        clone.per_changed_file_threshold = self.per_changed_file_threshold
        return clone
