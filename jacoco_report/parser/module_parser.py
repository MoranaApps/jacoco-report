"""
A module parser that parses the module information from the action inputs.
"""

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.model.module import Module


# pylint: disable=too-few-public-methods
class ModuleParser:
    """
    A class that parses the module information from the action inputs.
    """

    @staticmethod
    def parse(modules: dict[str, str], modules_thresholds: dict[str, (float, float)]) -> dict[str, Module]:
        """
        Parse the module information from the action inputs.
        If no threshold is provided for a module, the default threshold is used.

        Parameters:
            modules (dict[str, str]): The module names and their paths.
            modules_thresholds (dict[str, (float, float)]): The module names and their thresholds.

        Returns:
            dict[str, Module]: The module names and their Module objects.
        """
        module_dict = {}

        for name, path in modules.items():
            overall, changed = modules_thresholds.get(name, (None, None))
            module_dict[name] = Module(
                name,
                path,
                overall if overall is not None else ActionInputs.get_min_coverage_overall(),
                changed if changed is not None else ActionInputs.get_min_coverage_changed_files(),
            )

        return module_dict
