"""
A module that contains the Coverage class
"""

import logging

from jacoco_report.model.counter import Counter
from jacoco_report.utils.enums import MetricTypeEnum

logger = logging.getLogger(__name__)


# pylint: disable=too-few-public-methods
class Coverage:
    """
    A class that represents the coverage of a file
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self, instruction: Counter, branch: Counter, line: Counter, complexity: Counter, method: Counter, clazz: Counter
    ):
        """
        A constructor for the Coverage class

        Parameters:
            instruction (Counter): The instruction counter
            branch (Counter): The branch counter
            line (Counter): The line counter
            complexity (Counter): The complexity counter
            method (Counter): The method counter
            clazz (Counter): The class counter
        """
        self.instruction: Counter = instruction
        self.branch: Counter = branch
        self.line: Counter = line
        self.complexity: Counter = complexity
        self.method: Counter = method
        self.clazz: Counter = clazz

    # pylint: disable=too-many-return-statements
    def get_coverage_by_metric(self, metric_type: str) -> float:
        """
        Returns the coverage of the given counter

        Parameters:
            metric_type (str): The name of the counter

        Returns:
            Counter: The coverage of the given counter
        """
        match metric_type:
            case MetricTypeEnum.INSTRUCTION.value:
                return self.instruction.coverage()
            case MetricTypeEnum.BRANCH.value:
                return self.branch.coverage()
            case MetricTypeEnum.LINE.value:
                return self.line.coverage()
            case MetricTypeEnum.COMPLEXITY.value:
                return self.complexity.coverage()
            case MetricTypeEnum.METHOD.value:
                return self.method.coverage()
            case MetricTypeEnum.CLASS.value:
                return self.clazz.coverage()
            case _:
                logger.error("Unknown metric type: %s", metric_type)
                return Counter(0, 0).coverage()

    def get_values_by_metric(self, metric_type: str) -> tuple[int, int]:
        """
        Returns the values of the given counter

        Parameters:
            metric_type (str): The name of the counter

        Returns:
            Counter: The values of the given counter
        """
        if metric_type == MetricTypeEnum.INSTRUCTION.value:
            return self.instruction.missed, self.instruction.covered
        if metric_type == MetricTypeEnum.BRANCH.value:
            return self.branch.missed, self.branch.covered
        if metric_type == MetricTypeEnum.LINE.value:
            return self.line.missed, self.line.covered
        if metric_type == MetricTypeEnum.COMPLEXITY.value:
            return self.complexity.missed, self.complexity.covered
        if metric_type == MetricTypeEnum.METHOD.value:
            return self.method.missed, self.method.covered
        if metric_type == MetricTypeEnum.CLASS.value:
            return self.clazz.missed, self.clazz.covered

        logger.error("Unknown metric type: %s", metric_type)
        return 0, 0

    def __str__(self):
        """
        Returns the string representation of the Coverage class

        Returns:
            str: The string representation of the Coverage class
        """
        return (
            f"Instruction: {self.instruction}, Branch: {self.branch}, Line: {self.line}, "
            f"Complexity: {self.complexity}, Method: {self.method}, Class: {self.clazz}"
        )
