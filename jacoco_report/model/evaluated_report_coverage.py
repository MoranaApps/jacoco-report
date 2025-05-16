"""
A module that contains the EvaluatedCoverage class.
"""

from jacoco_report.model.counter import Counter


# pylint: disable=too-few-public-methods, too-many-instance-attributes
class EvaluatedReportCoverage:
    """
    A class that represents an evaluated coverage of one report file or module.
    """

    def __init__(self, name: str = "Unknown", module_name: str = "Unknown"):
        self.name: str = name
        self.module_name: str = module_name

        # PR comment data
        # summary data
        self.overall_passed: bool = True
        self.overall_coverage_reached: float = 0.0
        self.overall_coverage_threshold: float = 0.0
        self.overall_coverage: Counter = Counter(0, 0)  # to keep information about coverage weight

        self.sum_changed_files_passed: bool = True
        self.sum_changed_files_coverage_reached: float = 0.0
        self.sum_changed_files_coverage: Counter = Counter(0, 0)  # to keep information about coverage weight

        # per each changed file data
        self.changed_files_passed: dict[str, bool] = {}
        self.changed_files_threshold: float = 0.0
        self.changed_files_coverage_reached: dict[str, float] = {}

        self.per_changed_file_threshold: float = 0.0

    def to_dict(self) -> dict:
        """Convert object to dictionary for JSON serialization"""
        return {
            "name": self.name,
            "overall_passed": self.overall_passed,
            "overall_coverage_reached": self.overall_coverage_reached,
            "overall_coverage_threshold": self.overall_coverage_threshold,
            "overall_coverage": {"missed": self.overall_coverage.missed, "covered": self.overall_coverage.covered},
            "sum_changed_files_passed": self.sum_changed_files_passed,
            "sum_changed_files_coverage_reached": self.sum_changed_files_coverage_reached,
            "sum_changed_files_coverage": {
                "missed": self.sum_changed_files_coverage.missed,
                "covered": self.sum_changed_files_coverage.covered,
            },
            "changed_files_passed": self.changed_files_passed,
            "changed_files_threshold": self.changed_files_threshold,
            "changed_files_coverage_reached": self.changed_files_coverage_reached,
            "per_changed_file_threshold": self.per_changed_file_threshold,
        }
