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
    def parse(modules: dict[str, str], modules_thresholds: dict[str, tuple[float, float, float]]) -> dict[str, Module]:
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
            overall, changed, changed_per_file = modules_thresholds.get(
                name,
                (
                    ActionInputs.get_min_coverage_overall(),
                    ActionInputs.get_min_coverage_changed_files(),
                    ActionInputs.get_min_coverage_per_changed_file(),
                ),
            )
            module_dict[name] = Module(name, path, overall, changed, changed_per_file)

        return module_dict
