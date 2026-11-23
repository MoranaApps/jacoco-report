"""
This module contains the enums used in the jacoco_report package.
"""

from enum import StrEnum


class CommentLevelEnum(StrEnum):
    """
    A class representing the comment mode enum.
    """

    NONE = "none"
    MINIMAL = "minimal"
    FULL = "full"
    CHANGED = "changed"
    FAILED = "failed"
    FAILED_OR_CHANGED = "failed-or-changed"


class ReportTargetEnum(StrEnum):
    """
    A class representing where the report is written: the PR comment, the job summary, or both.
    """

    COMMENT = "comment"
    SUMMARY = "summary"
    BOTH = "both"


class MetricTypeEnum(StrEnum):
    """
    A class representing the metric type enum.
    """

    INSTRUCTION = "instruction"
    LINE = "line"
    BRANCH = "branch"
    COMPLEXITY = "complexity"
    METHOD = "method"
    CLASS = "class"


class FailOnThresholdEnum(StrEnum):
    """
    A class representing the fail on threshold enum.
    """

    OVERALL = "overall"
    CHANGED_FILES_AVERAGE = "changed-files-average"
    PER_CHANGED_FILE = "per-changed-file"
    FAIL_UNCHANGED = "fail-unchanged"
    NO_DECREASE = "no-decrease"
