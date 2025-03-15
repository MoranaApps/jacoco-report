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
