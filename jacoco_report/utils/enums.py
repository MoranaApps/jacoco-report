"""
This module contains the enums used in the jacoco_report package.
"""

from enum import StrEnum


class SensitivityEnum(StrEnum):
    """
    A class representing the sensitivity enum.
    """

    DETAIL = "detail"
    SUMMARY = "summary"
    MINIMAL = "minimal"


class CommentModeEnum(StrEnum):
    """
    A class representing the comment mode enum.
    """

    SINGLE = "single"
    MULTI = "multi"
    MODULE = "module"


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
