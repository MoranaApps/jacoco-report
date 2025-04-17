"""
A module for handling the inputs provided to the GH action.
"""

import logging
import sys
import re
from typing import Optional

from jacoco_report.utils.constants import (
    TOKEN,
    PATHS,
    EXCLUDE_PATHS,
    MIN_COVERAGE_OVERALL,
    MIN_COVERAGE_CHANGED_FILES,
    TITLE,
    SENSITIVITY,
    COMMENT_MODE,
    MODULES,
    MODULES_THRESHOLDS,
    SKIP_NOT_CHANGED,
    UPDATE_COMMENT,
    PASS_SYMBOL,
    FAIL_SYMBOL,
    FAIL_ON_THRESHOLD,
    DEBUG,
    METRIC,
    PR_NUMBER,
)

from jacoco_report.utils.enums import SensitivityEnum, CommentModeEnum, MetricTypeEnum
from jacoco_report.utils.gh_action import get_action_input
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)


# pylint: disable=too-many-branches, too-many-statements, too-many-locals, too-many-public-methods
class ActionInputs:
    """
    A class representing the inputs provided to the GH action.
    """

    @staticmethod
    def get_token() -> str:
        """
        Get the GitHub token from the action inputs.
        The value is provided by GitHub environment variable and define by GitHub.
        """
        return get_action_input(TOKEN)

    @staticmethod
    def get_paths(raw: bool = False) -> list[str] | str:
        """
        Get the paths from the action inputs.
        """
        paths = get_action_input(PATHS)

        if raw:
            return paths

        return ActionInputs.__parse_paths(paths)

    @staticmethod
    def get_exclude_paths(raw: bool = False) -> list[str] | str:
        """
        Get the exclude paths from the action inputs.
        """
        exclude_paths = get_action_input(EXCLUDE_PATHS)

        if raw:
            return exclude_paths

        return ActionInputs.__parse_paths(exclude_paths)

    @staticmethod
    def get_min_coverage_overall() -> float:
        """
        Get the minimum coverage overall from the action inputs.
        """
        return float(get_action_input(MIN_COVERAGE_OVERALL, "0.0"))

    @staticmethod
    def get_min_coverage_changed_files() -> float:
        """
        Get the minimum coverage changed files from the action inputs.
        """
        return float(get_action_input(MIN_COVERAGE_CHANGED_FILES, "0.0"))

    @staticmethod
    def get_title(report_name: Optional[str] = None) -> str:
        """
        Get the title from the action inputs.
        """
        title = get_action_input(TITLE, "")
        if len(title) > 0:
            match ActionInputs.get_comment_mode():
                case CommentModeEnum.MULTI:
                    return title + (report_name if report_name else "Unknown Report Name")
                case CommentModeEnum.MODULE:
                    return title + (report_name if report_name else "Unknown Report Name")
                case _:
                    return title

        match ActionInputs.get_comment_mode():
            case CommentModeEnum.MULTI:
                return "Report: " + (report_name if report_name else "Unknown Report Name")
            case CommentModeEnum.MODULE:
                return "Module: " + (report_name if report_name else "Unknown Report Name")
            case _:
                return "JaCoCo Coverage Report"

    @staticmethod
    def get_pr_number(gh: GitHub) -> Optional[int]:
        """
        Get the PR number from the GitHub environment variables.
        """
        pr_number = get_action_input(PR_NUMBER)
        if pr_number:
            return int(pr_number)

        pr_number: Optional[int] = gh.get_pr_number()  # type: ignore[no-redef]
        if pr_number:
            return pr_number

        logger.error("The PR number not detected.")
        return None

    @staticmethod
    def get_metric() -> str:
        """
        Get the metric from the action inputs.
        """
        return get_action_input(METRIC, MetricTypeEnum.INSTRUCTION)

    @staticmethod
    def get_sensitivity() -> str:
        """
        Get the sensitivity from the action inputs.
        """
        return get_action_input(SENSITIVITY, SensitivityEnum.DETAIL)

    @staticmethod
    def get_comment_mode() -> str:
        """
        Get the comment mode from the action inputs.
        """
        return get_action_input(COMMENT_MODE, CommentModeEnum.SINGLE)

    @staticmethod
    def get_modules(raw: bool = False) -> dict[str, str] | str:
        """
        Get the modules from the action inputs.
        """
        mods = get_action_input(MODULES, "").strip()

        if raw:
            return mods

        if ": " in mods:
            mods = mods.replace(": ", ":")

        split_by: str = "," if "," in mods else "\n"
        d = {}

        if len(mods) > 0:
            for mod in mods.split(split_by):
                # detect presence of '#' char - user commented out the line
                if "#" in mod:
                    continue

                # format string, clean up, ...
                formatted_mod = mod.strip()

                # create a dictionary record from formatted string
                key, value = formatted_mod.split(":")
                d[key] = value.strip()

        return d

    @staticmethod
    def get_modules_thresholds(raw: bool = False) -> dict[str, tuple[Optional[float], Optional[float]]] | str:
        """
        Get the modules thresholds from the action inputs.
        """

        def parse_module_thresholds(received: str) -> dict[str, tuple[Optional[float], Optional[float]]]:
            if len(received) == 0:
                return {}

            result = dict[str, tuple[Optional[float], Optional[float]]]()
            split_by: str = "," if "," in received else "\n"
            mts: list[str] = received.split(split_by)
            for mt in mts:
                # detect presence of '#' char - user commented out the line
                if "#" in mt:
                    continue

                # format string, clean up, ...
                formatted_mt = mt.strip()

                name, values = formatted_mt.split(":")
                f_name = name.strip()
                f_values = values.strip()
                parts = f_values.split("*")
                overall = float(parts[0]) if len(parts[0]) > 0 else None
                changed = float(parts[1]) if len(parts[1]) > 1 else None
                result[f_name] = (overall, changed)
            return result

        raw_input = get_action_input(MODULES_THRESHOLDS, "").strip()

        if raw:
            return raw_input

        if ": " in raw_input:
            raw_input = raw_input.replace(": ", ":")

        # return parse_module_thresholds(get_action_input(raw_input))
        return parse_module_thresholds(raw_input)

    @staticmethod
    def get_skip_not_changed() -> bool:
        """
        Get the skip not changed from the action inputs.
        """
        return get_action_input(SKIP_NOT_CHANGED, "false") == "true"

    @staticmethod
    def get_update_comment() -> bool:
        """
        Get the update comment from the action inputs.
        """
        return get_action_input(UPDATE_COMMENT, "true") == "true"

    @staticmethod
    def get_pass_symbol() -> str:
        """
        Get the pass symbol from the action inputs.
        """
        return get_action_input(PASS_SYMBOL, "✅")

    @staticmethod
    def get_fail_symbol() -> str:
        """
        Get the fail symbol from the action inputs.
        """
        return get_action_input(FAIL_SYMBOL, "❌")

    @staticmethod
    def get_fail_on_threshold() -> bool:
        """
        Get the fail on threshold from the action inputs.
        """
        return get_action_input(FAIL_ON_THRESHOLD, "true") == "true"

    @staticmethod
    def get_debug() -> bool:
        """
        Get the debug from the action inputs.
        """
        return get_action_input(DEBUG, "false") == "true"

    @staticmethod
    def get_baseline_paths(raw: bool = False) -> list[str] | str:
        """
        Get the baseline paths from the action inputs.
        """
        baseline_paths = get_action_input("baseline-paths")

        if raw:
            return baseline_paths

        return ActionInputs.__parse_paths(baseline_paths)

    @staticmethod
    def validate_module(module_touple: str) -> list[str]:
        """
        Validate the module string.

        Parameters:
            module_name (str): The module name string to validate.
            module_value (str): The module value string to validate.

        Returns:
            list: A list of errors if any.
        """
        # Check if the module is in the format 'module:module_path'
        if ":" not in module_touple or module_touple.count(":") > 1:
            return [
                f"'module':'{module_touple}' must be in the format 'module:module_path'. "
                f"Where module_path is relative from root of project. "
                f"Module value: {module_touple}"
            ]

        # Check if the module name is a non-empty string
        module_parts = module_touple.split(":")
        if not module_parts[0]:
            return [f"Module with value:'{module_parts[1]}' must have a non-empty name."]

        # Check if the module path is a non-empty string
        if not module_parts[1]:
            return [f"Module with 'name':'{module_parts[0]}' must have a non-empty path."]

        input_module_pattern = r"^[a-zA-Z0-9_][a-zA-Z0-9_ \/\\-]*$"

        # Check if the module name is alphanumeric
        if not re.match(input_module_pattern, module_parts[0]):
            return [f"'module_name':'{module_parts[0]}' must be alphanumeric with allowed (/\\-_)."]

        # Check if the module path is alphanumeric
        if not re.match(input_module_pattern, module_parts[1]):
            return [f"'module_path':'{module_parts[1]}' must be alphanumeric with allowed (/\\-_)."]

        return []

    # pylint: disable=too-many-return-statements
    @staticmethod
    def validate_module_threshold(input_module_threshold: str) -> list[str]:
        """
        Validate the module threshold string.

        Parameters:
            input_module_threshold (str): The module threshold string to validate.

        Returns:
            list: A list of errors if any.
        """
        # Check if the input is a non-empty string
        if not input_module_threshold:
            return ["'module-threshold' must be a non-empty string."]

        # Check if the module is in the format 'module:threshold'
        if ":" not in input_module_threshold:
            return [f"'module-threshold':'{input_module_threshold}' must be in the format 'module:threshold'."]

        # Check if the module name is a non-empty string
        module_threshold_parts = input_module_threshold.split(":")
        if not module_threshold_parts[0]:
            return [f"Module threshold with value:'{module_threshold_parts[1]}' must have a non-empty name."]

        # Check if the module threshold is a non-empty string
        if not module_threshold_parts[1]:
            return [f"Module threshold with 'name':'{module_threshold_parts[0]}' must have a non-empty threshold."]

        # Check if the module threshold is the format containing '*'
        if "*" not in module_threshold_parts[1]:
            return [
                f"'module_threshold':'{module_threshold_parts[1]}' must contain '*' to split overall "
                f"and changed files threshold."
            ]

        errors = []
        # Check if the module threshold defined values are float or None
        # Overall
        values = module_threshold_parts[1].split("*")
        if len(values[0]) == 0:
            pass
        else:
            try:
                float(values[0])
            except ValueError:
                errors.append(f"'module_threshold' overall value '{values[0]}' must be a float or None.")

        # Changed
        if len(values[1]) == 0:
            pass
        else:
            try:
                float(values[1])
            except ValueError:
                errors.append(f"'module_threshold' changed files value '{values[1]}' must be a float or None.")

        return errors

    @staticmethod
    def is_valid_github_token(token: str) -> bool:
        """
        Check if the token format matches GitHub patterns.

        Parameters:
            token (str): The token to validate.

        Returns:
            bool: True if the token is valid, False otherwise.
        """

        # Check if the token format matches GitHub patterns
        token_pattern = r"^(gh[ps]_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})$"
        # token_pattern = r"^ghp_[a-zA-Z0-9]{36}$"
        if bool(re.match(token_pattern, token)):
            return True
        return False

    @staticmethod
    def validate_inputs() -> None:
        """
        Validates the inputs provided for the GH action.
        """
        errors = []

        token = ActionInputs.get_token()
        if not isinstance(token, str) or not token.strip():
            errors.append("'token' must be a non-empty string.")
        elif not ActionInputs.is_valid_github_token(token):
            errors.append("'token' must be a valid GitHub token.")

        paths = ActionInputs.get_paths(raw=True)
        if paths is None:
            errors.append("'paths' must be defined.")
        elif not isinstance(paths, str):
            errors.append("'paths' must be a list of strings.")
        elif len(paths) == 0:
            errors.append("'paths' must be a non-empty list of strings.")

        exclude_paths = ActionInputs.get_exclude_paths(raw=True)
        # if not isinstance(exclude_paths, str):
        #     errors.append("'exclude-paths' must be a list of strings or not defined.")

        min_coverage_overall = ActionInputs.get_min_coverage_overall()
        if not isinstance(min_coverage_overall, float) or min_coverage_overall < 0 or min_coverage_overall > 100:
            errors.append("'min-coverage-overall' must be a float between 0 and 100.")

        min_coverage_changed_files = ActionInputs.get_min_coverage_changed_files()
        if (
            not isinstance(min_coverage_changed_files, float)
            or min_coverage_changed_files < 0
            or min_coverage_changed_files > 100
        ):
            errors.append("'min-coverage-changed-files' must be a float between 0 and 100.")

        metric = ActionInputs.get_metric()
        if not isinstance(metric, str) or metric not in MetricTypeEnum:
            errors.append(
                "'metric' must be a string from these options: 'instruction', "
                "'line', 'branch', 'complexity', 'method', 'class'."
            )

        sensitivity = ActionInputs.get_sensitivity()
        if not isinstance(sensitivity, str) or sensitivity not in SensitivityEnum:
            errors.append("'sensitivity' must be a string from these options: 'minimal', 'summary', 'detail'.")

        comment_mode = ActionInputs.get_comment_mode()
        if not isinstance(comment_mode, str) or comment_mode not in CommentModeEnum:
            errors.append("'comment-mode' must be a string from these options: 'single', 'multi', 'module'.")

        modules: dict[str, str] | str = ActionInputs.get_modules(raw=True)
        if not isinstance(modules, str):
            errors.append("'modules' must be a string or not defined.")
        else:
            if ": " in modules:
                modules = modules.replace(": ", ":")

            if len(modules) == 0:
                pass
            elif len(modules) < 3 or ":" not in modules:
                errors.append("'modules' must be a list of strings in format 'module:relative_path'.")
            else:
                split_by: str = "," if "," in modules else "\n"
                f_modules = modules.split(split_by)
                for module in f_modules:
                    errors.extend(ActionInputs.validate_module(module))

        if (
            comment_mode == CommentModeEnum.MODULE
            and len(ActionInputs.get_modules().keys()) == 0  # type: ignore[union-attr]
        ):  # type: ignore[union-attr]
            errors.append("'comment-mode' is 'module' but 'modules' is not defined.")

        modules_thresholds: dict[str, tuple[Optional[float], Optional[float]]] | str = (
            ActionInputs.get_modules_thresholds(raw=True)
        )
        if not isinstance(modules_thresholds, str):
            errors.append("'modules-thresholds' must be a string or not defined.")
        else:
            if ": " in modules_thresholds:
                modules_thresholds = modules_thresholds.replace(": ", ":")

            if len(modules_thresholds) == 0:
                pass
            elif len(modules_thresholds) < 3 or ":" not in modules_thresholds:
                errors.append("'modules-thresholds' must be a list of strings in format 'module:overall*changed'.")
            else:
                split_by: str = "," if "," in modules_thresholds else "\n"  # type: ignore[no-redef]
                f_modules_thresholds = modules_thresholds.split(split_by)
                for module_threshold in f_modules_thresholds:
                    errors.extend(ActionInputs.validate_module_threshold(module_threshold))

        skip_not_changed = ActionInputs.get_skip_not_changed()
        if not isinstance(skip_not_changed, bool):
            errors.append("'skip-not-changed' must be a boolean.")

        baseline_paths = ActionInputs.get_baseline_paths(raw=True)
        # if not isinstance(baseline_paths, str):
        #     errors.append("'baseline-paths' must be a list of strings or not defined.")

        update_comment = ActionInputs.get_update_comment()
        if not isinstance(update_comment, bool):
            errors.append("'update-comment' must be a boolean.")

        pass_symbol = ActionInputs.get_pass_symbol()
        if not isinstance(pass_symbol, str) or not pass_symbol.strip() or len(pass_symbol) < 1:
            errors.append("'pass-symbol' must be a non-empty string and have a length from 1.")

        fail_symbol = ActionInputs.get_fail_symbol()
        if not isinstance(fail_symbol, str) or not fail_symbol.strip() or len(fail_symbol) < 1:
            errors.append("'fail-symbol' must be a non-empty string and have a length from 1.")

        fail_on_threshold = ActionInputs.get_fail_on_threshold()
        if not isinstance(fail_on_threshold, bool):
            errors.append("'fail-on-threshold' must be a boolean.")

        debug = ActionInputs.get_debug()
        if not isinstance(debug, bool):
            errors.append("'debug' must be a boolean.")

        # Log errors if any
        if errors:
            for error in errors:
                logger.error(error)
            sys.exit(1)

        logger.debug("Paths: %s", paths)
        logger.debug("Exclude paths: %s", exclude_paths)
        logger.debug("Minimum coverage overall: %s", min_coverage_overall)
        logger.debug("Minimum coverage changed files: %s", min_coverage_changed_files)
        logger.debug("Title: %s", ActionInputs.get_title())
        logger.debug("Metric: %s", metric)
        logger.debug("Sensitivity: %s", sensitivity)
        logger.debug("Comment mode: %s", comment_mode)
        logger.debug("Modules: %s", modules)
        logger.debug("Modules thresholds: %s", modules_thresholds)
        logger.debug("Skip not changed: %s", skip_not_changed)
        logger.debug("Baseline paths: %s", baseline_paths)
        logger.debug("Update comment: %s", update_comment)
        logger.debug("Pass symbol: %s", pass_symbol)
        logger.debug("Fail symbol: %s", fail_symbol)
        logger.debug("Fail on threshold: %s", fail_on_threshold)
        logger.debug("Debug logging: %s", debug)

        logger.info("Action inputs validated successfully.")

    # methods for getting the inputs not provided by the user but expected from GitHub
    @staticmethod
    def get_event_name() -> str:
        """
        Get the event name from the GitHub environment variables.
        """
        return get_action_input("GITHUB_EVENT_NAME", prefix="")

    # methods for getting the inputs not provided by the user but expected from GitHub
    @staticmethod
    def get_repository() -> str:
        """
        Get the repository from the GitHub environment variables.
        """
        return get_action_input("GITHUB_REPOSITORY", prefix="")

    @staticmethod
    def __parse_paths(paths: Optional[str]) -> list[str]:
        """
        Parse the paths from the action inputs.
        """
        if paths is None:
            return []

        res: list[str] = []
        for path in paths.splitlines():
            # detect presence of '#' char - user commented out the line
            if path.strip().startswith("#"):
                continue

            # format string, clean up, ...
            formatted_path = path.strip()
            if len(formatted_path) > 0:
                res.append(formatted_path.strip())

        return res
