"""
A module for handling the inputs provided to the GH action.
"""

import logging
import sys
import re
from typing import Literal, Optional, overload

from jacoco_report.utils.constants import (
    TOKEN,
    PATHS,
    EXCLUDE_PATHS,
    GLOBAL_THRESHOLDS,
    TITLE,
    COMMENT_LEVEL,
    MODULES,
    MODULES_THRESHOLDS,
    SKIP_UNCHANGED,
    UPDATE_COMMENT,
    PASS_SYMBOL,
    FAIL_SYMBOL,
    FAIL_ON_THRESHOLD,
    DEBUG,
    METRIC,
    PR_NUMBER,
    DEFAULT_GLOBAL_THRESHOLDS,
)

from jacoco_report.utils.enums import CommentLevelEnum, MetricTypeEnum, FailOnThresholdEnum
from jacoco_report.utils.gh_action import get_action_input
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)


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

    @overload
    @staticmethod
    def get_paths(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_paths(raw: Literal[False] = ...) -> list[str]: ...
    @staticmethod
    def get_paths(raw: bool = False) -> list[str] | str:
        """
        Get the paths from the action inputs.
        """
        paths = get_action_input(PATHS)

        if raw:
            return paths

        return ActionInputs.__parse_paths(paths)

    @overload
    @staticmethod
    def get_exclude_paths(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_exclude_paths(raw: Literal[False] = ...) -> list[str]: ...
    @staticmethod
    def get_exclude_paths(raw: bool = False) -> list[str] | str:
        """
        Get the exclude paths from the action inputs.
        """
        exclude_paths = get_action_input(EXCLUDE_PATHS)

        if raw:
            return exclude_paths

        return ActionInputs.__parse_paths(exclude_paths)

    @overload
    @staticmethod
    def get_global_thresholds(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_global_thresholds(raw: Literal[False] = ...) -> tuple[float, float, float]: ...
    @staticmethod
    def get_global_thresholds(raw: bool = False) -> tuple[float, float, float] | str:
        """Return the global coverage thresholds as a tuple."""

        def safe_float(value: str, label: str) -> float:
            try:
                return float(value) if value else 0.0
            except ValueError:
                logger.error("Warning: Cannot convert '%s' part ('%s') to float. Defaulting to 0.0.", label, value)
                return 0.0

        raw_value = get_action_input(GLOBAL_THRESHOLDS, DEFAULT_GLOBAL_THRESHOLDS).strip()
        cleaned = ActionInputs.__clean_from_comment(raw_value)

        if raw:
            return cleaned

        if "*" not in cleaned:
            logger.warning("'global-thresholds' input is not formatted correctly. ")
            cleaned = DEFAULT_GLOBAL_THRESHOLDS

        if cleaned.count("*") == 1:
            logger.warning(
                "'global-thresholds' input is not formatted correctly. "
                "Adding default value for changed file threshold."
            )
            cleaned += "*0.0"

        parts = cleaned.split("*")
        overall = safe_float(parts[0], "overall")
        changed = safe_float(parts[1], "changed files average")
        per_file = safe_float(parts[2], "changed file")

        return overall, changed, per_file

    @staticmethod
    def _get_global_threshold_component(index: int, component_name: str) -> float:
        """Helper method to extract a specific component from global thresholds."""
        thresholds = ActionInputs.get_global_thresholds()
        if isinstance(thresholds, str):
            logger.error(
                "Global thresholds input is not formatted correctly. Returning default value 0.0 for %s.",
                component_name,
            )
            return 0.0
        return thresholds[index]

    @staticmethod
    def get_global_overall_threshold() -> float:
        """
        Get the minimum coverage overall from the action inputs.
        """
        return ActionInputs._get_global_threshold_component(0, "overall threshold")

    @staticmethod
    def get_global_changed_files_average_threshold() -> float:
        """
        Get the minimum average coverage changed files from the action inputs.
        """
        return ActionInputs._get_global_threshold_component(1, "changed files average threshold")

    @staticmethod
    def get_global_changed_file_threshold() -> float:
        """
        Get the minimum coverage per changed file from the action inputs.
        """
        return ActionInputs._get_global_threshold_component(2, "changed file threshold")

    @staticmethod
    def get_title() -> str:
        """
        Get the title from the action inputs.
        """
        title = get_action_input(TITLE, "")
        if len(title) > 0:
            return title

        return "JaCoCo Coverage Report"

    @staticmethod
    def get_pr_number(gh: GitHub) -> Optional[int]:
        """
        Get the PR number from the GitHub environment variables.
        """
        pr_input = get_action_input(PR_NUMBER)
        if pr_input:
            return int(pr_input)

        pr_number: Optional[int] = gh.get_pr_number()
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
    def get_comment_level() -> str:
        """
        Get the comment level from the action inputs.
        """
        return get_action_input(COMMENT_LEVEL, CommentLevelEnum.FULL)

    @overload
    @staticmethod
    def get_modules(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_modules(raw: Literal[False] = ...) -> dict[str, str]: ...
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
                cleaned_mod = ActionInputs.__clean_from_comment(mod)
                if len(cleaned_mod) == 0:
                    continue

                # create a dictionary record from formatted string
                key, value = cleaned_mod.split(":")
                d[key] = value.strip()

        return d

    @overload
    @staticmethod
    def get_modules_thresholds(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_modules_thresholds(raw: Literal[False] = ...) -> dict[str, tuple[float, float, float]]: ...
    @staticmethod
    def get_modules_thresholds(raw: bool = False) -> dict[str, tuple[float, float, float]] | str:
        """
        Get the modules thresholds from the action inputs.
        """

        def parse_module_thresholds(received: str) -> dict[str, tuple[float, float, float]]:
            if len(received) == 0:
                return {}

            result = dict[str, tuple[float, float, float]]()
            split_by: str = "," if "," in received else "\n"
            mts: list[str] = received.split(split_by)
            for mt in mts:
                # format string, clean up, ...
                cleaned_mt = ActionInputs.__clean_from_comment(mt)

                if len(cleaned_mt) == 0:
                    continue

                name, values = cleaned_mt.split(":")
                f_name = name.strip()
                f_values = values.strip()
                parts = f_values.split("*")

                overall = float(parts[0]) if len(parts[0]) > 0 else ActionInputs.get_global_overall_threshold()
                changed = (
                    float(parts[1]) if len(parts[1]) > 0 else ActionInputs.get_global_changed_files_average_threshold()
                )
                changed_per_file = (
                    float(parts[2]) if len(parts[2]) > 0 else ActionInputs.get_global_changed_file_threshold()
                )
                result[f_name] = (overall, changed, changed_per_file)
            return result

        raw_input = get_action_input(MODULES_THRESHOLDS, "").strip()

        if raw:
            return raw_input

        if ": " in raw_input:
            raw_input = raw_input.replace(": ", ":")

        # return parse_module_thresholds(get_action_input(raw_input))
        return parse_module_thresholds(raw_input)

    @staticmethod
    def get_skip_unchanged() -> bool:
        """
        Get the skip unchanged from the action inputs.
        """
        return get_action_input(SKIP_UNCHANGED, "false") == "true"

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
    def get_fail_on_threshold() -> list[str]:
        """
        Get the threshold levels that should trigger a failure.
        Supports:
          - "true": fail on all thresholds
          - "false": do not fail
          - Comma or newline separated of supported thresholds: overall, changed-files-average, per-changed-file
        """
        value = get_action_input(FAIL_ON_THRESHOLD, "overall,changed-files-average,per-changed-file").strip().lower()

        if value == "false":
            logger.warning(
                "Boolean value for fail-on-threshold is no longer supported from v3. "
                "Use an empty string to disable threshold failure."
            )
            return []

        if value == "true":
            logger.warning(
                "Boolean value for fail-on-threshold is no longer supported from v3. "
                "Use comma-separated values to fail on thresholds: "
                "overall,changed-files-average,per-changed-file"
            )
            return [
                FailOnThresholdEnum.OVERALL.value,
                FailOnThresholdEnum.CHANGED_FILES_AVERAGE.value,
                FailOnThresholdEnum.PER_CHANGED_FILE.value,
            ]

        # Split on newlines and commas
        raw_items: list[str] = [v.strip() for line in value.splitlines() for v in line.split(",") if v.strip()]

        # Check for validity of the items
        valid_values = {e.value for e in FailOnThresholdEnum}
        invalid_items = [item for item in raw_items if item not in valid_values]
        if invalid_items:
            raise ValueError(f"Unsupported threshold levels: {', '.join(invalid_items)}")

        return [FailOnThresholdEnum(item).value for item in raw_items]

    @staticmethod
    def get_debug() -> bool:
        """
        Get the debug from the action inputs.
        """
        return get_action_input(DEBUG, "false") == "true"

    @overload
    @staticmethod
    def get_baseline_paths(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_baseline_paths(raw: Literal[False] = ...) -> list[str]: ...
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

    @staticmethod
    def validate_module_threshold(input_module_threshold: str) -> list[str]:
        """
        Validate the module threshold string.

        Parameters:
            input_module_threshold (str): The module threshold string to validate.

        Returns:
            list: A list of errors if any.
        """
        # Check if the module is in the format 'module:threshold'
        if ":" not in input_module_threshold or input_module_threshold.count(":") > 1:
            return [f"'module-threshold':'{input_module_threshold}' must be in the format 'module:threshold'."]

        # Check if the module name is a non-empty string
        module_threshold_parts = input_module_threshold.split(":")
        if not module_threshold_parts[0]:
            return [f"Module threshold with value:'{module_threshold_parts[1]}' must have a non-empty name."]

        # Check if the module threshold is a non-empty string
        if not module_threshold_parts[1]:
            return [f"Module threshold with 'name':'{module_threshold_parts[0]}' must have a non-empty threshold."]

        # Check if the module threshold is the format containing '*'
        if module_threshold_parts[1].count("*") != 2:
            return [
                f"'module-threshold':'{module_threshold_parts[1]}' must contain two '*' to split overall, "
                f"changed files and changed per file threshold."
            ]

        errors = []
        # Check if the module threshold defined values are float or None
        # Overall
        values = module_threshold_parts[1].split("*")
        if len(values[0]) == 0:
            # if the value is empty, it means that the user wants to use the default value
            pass
        else:
            try:
                float(values[0])
            except ValueError:
                errors.append(f"'module-threshold' overall value '{values[0]}' must be a float or None.")

        # Changed
        if len(values[1]) == 0:
            # if the value is empty, it means that the user wants to use the default value
            pass
        else:
            try:
                float(values[1])
            except ValueError:
                errors.append(f"'module-threshold' changed files value '{values[1]}' must be a float or None.")

        # Changed per file
        if len(values[2]) == 0:
            # if the value is empty, it means that the user wants to use the default value
            pass
        else:
            try:
                float(values[2])
            except ValueError:
                errors.append(f"'module-threshold' changed per file value '{values[2]}' must be a float or None.")

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

        def is_float(value: str) -> bool:
            try:
                float(value)
                return True
            except ValueError:
                return False

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

        global_thresholds = ActionInputs.get_global_thresholds(raw=True)
        if not isinstance(global_thresholds, str):
            errors.append("'global-thresholds' must be a string or not defined.")
        elif "*" not in global_thresholds:
            errors.append(
                "'global-thresholds' must be in the format 'overall*changed_files_average*changed_file'. "
                "Where overall is the minimum coverage overall, changed_files_average is the minimum average coverage "
                "of changed files and changed_file is the minimum coverage per changed file."
            )
        else:
            if global_thresholds.count("*") == 1:
                logger.warning(
                    "'global-thresholds' should be in the format 'overall*changed_files_average*changed_file'. "
                    "Adding default value for changed file threshold."
                )
                global_thresholds += "*0.0"
            parts = global_thresholds.split("*")
            if not is_float(parts[0]) or float(parts[0]) < 0 or float(parts[0]) >= 100:
                errors.append("'global-thresholds' overall value must be a float between 0 and 100.")
            if not is_float(parts[1]) or float(parts[1]) < 0 or float(parts[1]) >= 100:
                errors.append(
                    "'global-thresholds' changed_files_average files value must be a float between 0 and 100."
                )
            if not is_float(parts[2]) or float(parts[2]) < 0 or float(parts[2]) >= 100:
                errors.append("'global-thresholds' changed-file value must be a float between 0 and 100.")

        metric = ActionInputs.get_metric()
        if not isinstance(metric, str) or metric not in MetricTypeEnum:
            errors.append(
                "'metric' must be a string from these options: 'instruction', "
                "'line', 'branch', 'complexity', 'method', 'class'."
            )

        comment_level = ActionInputs.get_comment_level()
        if not isinstance(comment_level, str) or comment_level not in CommentLevelEnum:
            errors.append("'comment-level' must be a string from these options: 'minimal', 'full'.")

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

        modules_thresholds: dict[str, tuple[float, float, float]] | str = ActionInputs.get_modules_thresholds(raw=True)
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
                split_by = "," if "," in modules_thresholds else "\n"  # type: ignore[no-redef]
                f_modules_thresholds = modules_thresholds.split(split_by)
                for module_threshold in f_modules_thresholds:
                    cleaned_module_threshold = ActionInputs.__clean_from_comment(module_threshold)
                    if len(cleaned_module_threshold) > 0:
                        errors.extend(ActionInputs.validate_module_threshold(cleaned_module_threshold))

        skip_unchanged = ActionInputs.get_skip_unchanged()
        if not isinstance(skip_unchanged, bool):
            errors.append("'skip-unchanged' must be a boolean.")

        update_comment = ActionInputs.get_update_comment()
        if not isinstance(update_comment, bool):
            errors.append("'update-comment' must be a boolean.")

        pass_symbol = ActionInputs.get_pass_symbol()
        if not isinstance(pass_symbol, str) or not pass_symbol.strip() or len(pass_symbol) < 1:
            errors.append("'pass-symbol' must be a non-empty string and have a length from 1.")

        fail_symbol = ActionInputs.get_fail_symbol()
        if not isinstance(fail_symbol, str) or not fail_symbol.strip() or len(fail_symbol) < 1:
            errors.append("'fail-symbol' must be a non-empty string and have a length from 1.")

        try:
            fail_on_threshold = ActionInputs.get_fail_on_threshold()
        except ValueError as e:
            errors.append(str(e))

        debug = ActionInputs.get_debug()
        if not isinstance(debug, bool):
            errors.append("'debug' must be a boolean.")

        logger.info(
            "[CONFIGURATION] Received input values:\n"
            "Paths: %s\n"
            "Exclude paths: %s\n"
            "Baseline paths: %s\n"
            "\n"
            "Global thresholds: overall=%s, avg_changed_files=%s, changed_file=%s\n"
            "\n"
            "Modules: %s\n"
            "Modules thresholds: %s\n"
            "\n"
            "Metric: %s\n"
            "Title: %s\n"
            "Comment level: %s\n"
            "\n"
            "Skip unchanged: %s\n"
            "Update comment: %s\n"
            "Fail on threshold: %s\n"
            "Debug logging enabled: %s\n"
            "Pass symbol: %s\n"
            "Fail symbol: %s",
            ActionInputs.get_paths(),
            ActionInputs.get_exclude_paths(),
            ActionInputs.get_baseline_paths(),
            ActionInputs.get_global_overall_threshold(),
            ActionInputs.get_global_changed_files_average_threshold(),
            ActionInputs.get_global_changed_file_threshold(),
            ActionInputs.get_modules(),
            ActionInputs.get_modules_thresholds(),
            ActionInputs.get_metric(),
            ActionInputs.get_title(),
            ActionInputs.get_comment_level(),
            ActionInputs.get_skip_unchanged(),
            ActionInputs.get_update_comment(),
            fail_on_threshold if fail_on_threshold else [],
            ActionInputs.get_debug(),
            ActionInputs.get_pass_symbol(),
            ActionInputs.get_fail_symbol(),
        )

        # Log errors if any
        if errors:
            for error in errors:
                logger.error(error)
            sys.exit(1)

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
    def __parse_paths(paths: str) -> list[str]:
        """
        Parse the paths from the action inputs.
        """
        if not paths:
            return []

        res: list[str] = []
        for path in paths.splitlines():
            cleaned_path = ActionInputs.__clean_from_comment(path)
            if len(cleaned_path) == 0:
                continue

            res.append(cleaned_path)

        return res

    @staticmethod
    def __clean_from_comment(input_string: str) -> str:
        """
        Clean the input string from comments.
        Examples:
            "path/to/file # this is a comment" -> "path/to/file"
            "# this is a comment" -> ""
            "   # this is a comment" -> ""
            "   path/to/file # this is a comment" -> "path/to/file"
        """
        if "#" in input_string:
            return input_string.split("#")[0].strip()
        return input_string.strip()
