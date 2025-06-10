"""
This module contains the enums used in the jacoco_report package.
"""

from enum import StrEnum


class CommentLevelEnum(StrEnum):
    """
    A class representing the comment mode enum.
    """

    MINIMAL = "minimal"
    FULL = "full"


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
