"""
A module for handling the inputs provided to the GH action.
"""

import logging
import sys
import re
from typing import Literal, Optional, overload

import yaml

from jacoco_report.utils.constants import (
    TOKEN,
    PATHS,
    EXCLUDE_PATHS,
    GLOBAL_THRESHOLDS,
    TITLE,
    COMMENT_LEVEL,
    REPORT_GROUPS,
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

from jacoco_report.model.report_group import ReportGroup
from jacoco_report.utils.enums import CommentLevelEnum, MetricTypeEnum, FailOnThresholdEnum
from jacoco_report.utils.gh_action import get_action_input
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)


def _is_valid_threshold_float(value: str) -> bool:
    try:
        f = float(value)
        return 0.0 <= f < 100.0
    except ValueError:
        return False


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
    def get_report_groups(raw: Literal[True]) -> str: ...

    @overload
    @staticmethod
    def get_report_groups(raw: Literal[False] = ...) -> list[ReportGroup]: ...

    @staticmethod
    def get_report_groups(raw: bool = False) -> list[ReportGroup] | str:
        """
        Get the report groups from the action inputs.
        Returns a list of ReportGroup objects parsed from the YAML input,
        or the raw string when raw=True.
        """
        raw_input = get_action_input(REPORT_GROUPS, "").strip()

        if raw:
            return raw_input

        if not raw_input:
            return []

        try:
            data = yaml.safe_load(raw_input)
        except yaml.YAMLError as e:
            raise ValueError(f"'report-groups' is not valid YAML: {e}") from e

        if not isinstance(data, list):
            raise ValueError("'report-groups' must be a YAML list.")

        groups: list[ReportGroup] = []
        for i, entry in enumerate(data):
            # Validate entry is a dict
            if not isinstance(entry, dict):
                raise ValueError(
                    f"'report-groups' entry #{i + 1} must be a YAML mapping (dict), got {type(entry).__name__}."
                )

            # Validate required keys
            if "name" not in entry or not entry.get("name"):
                raise ValueError(f"'report-groups' entry #{i + 1} must have a non-empty 'name' key.")

            if "paths" not in entry:
                raise ValueError(f"'report-groups' entry #{i + 1} must have a 'paths' key.")

            paths = entry["paths"]
            if not isinstance(paths, list):
                raise ValueError(f"'report-groups' entry #{i + 1} 'paths' must be a list, got {type(paths).__name__}.")

            if not paths or not all(isinstance(p, str) and p for p in paths):
                raise ValueError(
                    f"'report-groups' entry #{i + 1} 'paths' must be a non-empty list of non-empty strings."
                )

            name = entry["name"]
            baseline_paths = entry["baseline-paths"] if "baseline-paths" in entry else None

            thresholds_str = entry.get("thresholds", "")
            overall: Optional[float] = None
            changed: Optional[float] = None
            per_file: Optional[float] = None
            if thresholds_str:
                parts = str(thresholds_str).split("*")
                overall = float(parts[0]) if len(parts) > 0 and parts[0] else None
                changed = float(parts[1]) if len(parts) > 1 and parts[1] else None
                per_file = float(parts[2]) if len(parts) > 2 and parts[2] else None

            groups.append(ReportGroup(name, paths, overall, changed, per_file, baseline_paths))

        return groups

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
                "Use comma- or newline-separated values to fail on thresholds: "
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
    def validate_report_groups(raw_input: str) -> list[str]:
        """
        Validate the report-groups YAML input string.
        """
        errors: list[str] = []
        if not raw_input:
            return errors
        try:
            data = yaml.safe_load(raw_input)
        except yaml.YAMLError as e:
            return [f"'report-groups' is not valid YAML: {e}"]

        if not isinstance(data, list):
            return ["'report-groups' must be a YAML list."]

        for i, entry in enumerate(data):
            prefix = f"'report-groups' entry #{i + 1}"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be a YAML mapping.")
                continue
            if not entry.get("name"):
                errors.append(f"{prefix} must have a non-empty 'name'.")
            paths = entry.get("paths")
            if not paths or not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths):
                errors.append(f"{prefix} must have a non-empty 'paths' list of non-empty strings.")
            thresholds_str = entry.get("thresholds", "")
            if thresholds_str:
                parts = str(thresholds_str).split("*")
                if len(parts) != 3:
                    errors.append(f"{prefix} 'thresholds' must be in format 'O*A*P' (e.g. '80*70*60').")
                else:
                    for label, v in zip(("overall", "avg-changed", "per-file"), parts):
                        if v and not _is_valid_threshold_float(v):
                            errors.append(f"{prefix} 'thresholds' {label} value '{v}' must be a float in [0, 100).")
            baseline_paths = entry.get("baseline-paths", [])
            if baseline_paths is not None and not isinstance(baseline_paths, list):
                errors.append(f"{prefix} 'baseline-paths' must be a list.")
            elif baseline_paths is not None and not all(isinstance(p, str) and p for p in baseline_paths):
                errors.append(f"{prefix} 'baseline-paths' must be a list of non-empty strings.")
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

        # Validate paths: required unless report-groups is configured
        report_groups_raw: str = ActionInputs.get_report_groups(raw=True)
        has_report_groups = False
        if report_groups_raw and report_groups_raw.strip():
            try:
                report_groups_data = yaml.safe_load(report_groups_raw)
                has_report_groups = isinstance(report_groups_data, list) and len(report_groups_data) > 0
            except yaml.YAMLError:
                # Invalid YAML is reported by validate_report_groups below.
                has_report_groups = False

        paths = ActionInputs.get_paths(raw=True)
        if paths is None:
            errors.append("'paths' must be defined.")
        elif not isinstance(paths, str):
            errors.append("'paths' must be a list of strings.")
        else:
            # Check parsed paths list (which strips whitespace) instead of raw string length
            parsed_paths = ActionInputs.get_paths()
            if not parsed_paths and not has_report_groups:
                # paths is required only if report-groups is not configured
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

        errors.extend(ActionInputs.validate_report_groups(report_groups_raw))

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
            "Report groups: %s\n"
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
            report_groups_raw,
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
