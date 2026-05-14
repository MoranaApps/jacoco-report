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
    DEFAULT_GLOBAL_THRESHOLDS,
    REPORT_THRESHOLDS_DEFAULT,
    DEFAULT_REPORT_THRESHOLDS_DEFAULT,
    TITLE,
    COMMENT_LEVEL,
    REPORT_GROUPS,
    SKIP_UNCHANGED,
    EVALUATE_UNCHANGED,
    UPDATE_COMMENT,
    PASS_SYMBOL,
    FAIL_SYMBOL,
    FAIL_ON_THRESHOLD,
    DEBUG,
    METRIC,
    PR_NUMBER,
    BASELINE_PATHS,
    GITHUB_RUN_ID,
    GITHUB_RUN_STARTED_AT,
    GITHUB_ACTION_REF,
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

        return ActionInputs.__get_thresholds_input(
            input_name=GLOBAL_THRESHOLDS,
            default_value=DEFAULT_GLOBAL_THRESHOLDS,
            warning_input_label="global-thresholds",
            third_component_label="changed file",
            raw=raw,
        )

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

    @overload
    @staticmethod
    def get_report_thresholds_default(raw: Literal[True]) -> str: ...
    @overload
    @staticmethod
    def get_report_thresholds_default(raw: Literal[False] = ...) -> tuple[float, float, float]: ...
    @staticmethod
    def get_report_thresholds_default(raw: bool = False) -> tuple[float, float, float] | str:
        """Return the report-level default thresholds as a tuple (overall, avg-changed, per-file).

        These are used as field-level fallbacks for per-group thresholds when a group omits a field.
        global-thresholds is a separate evaluation pass and is never in this chain.
        """

        return ActionInputs.__get_thresholds_input(
            input_name=REPORT_THRESHOLDS_DEFAULT,
            default_value=DEFAULT_REPORT_THRESHOLDS_DEFAULT,
            warning_input_label="report-thresholds-default",
            third_component_label="per-changed-file",
            raw=raw,
        )

    @staticmethod
    def __get_thresholds_input(
        input_name: str,
        default_value: str,
        warning_input_label: str,
        third_component_label: str,
        raw: bool = False,
    ) -> tuple[float, float, float] | str:
        """Normalize O*A*P threshold input and parse it into three float components."""

        def safe_float(value: str, label: str) -> float:
            try:
                return float(value) if value else 0.0
            except ValueError:
                logger.warning("Cannot convert '%s' part ('%s') to float. Defaulting to 0.0.", label, value)
                return 0.0

        raw_value = get_action_input(input_name, default_value).strip()
        cleaned = ActionInputs.__clean_from_comment(raw_value)

        if raw:
            return cleaned

        if "*" not in cleaned:
            logger.warning("'%s' input is not formatted correctly.", warning_input_label)
            cleaned = default_value

        if cleaned.count("*") == 1:
            logger.warning(
                "'%s' input is not formatted correctly. Adding default value for %s threshold.",
                warning_input_label,
                third_component_label,
            )
            cleaned += "*0.0"

        parts = cleaned.split("*")
        overall = safe_float(parts[0], "overall")
        changed = safe_float(parts[1], "changed-files-average")
        per_file = safe_float(parts[2], third_component_label)

        return overall, changed, per_file

    @staticmethod
    def get_title() -> str:
        """
        Get the title from the action inputs.
        """
        title = get_action_input(TITLE, "").strip()
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
            try:
                return int(pr_input)
            except ValueError:
                logger.error("'pr-number' input '%s' is not a valid integer.", pr_input)
                return None

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

        errors = ActionInputs.validate_report_groups(raw_input)
        if errors:
            raise ValueError("; ".join(errors))

        data = yaml.safe_load(raw_input)
        if not isinstance(data, list):
            # Defensive guard; validate_report_groups already enforces this.
            raise ValueError("'report-groups' must be a YAML list.")

        groups: list[ReportGroup] = []
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                # Defensive guard; validate_report_groups already enforces this.
                raise ValueError(
                    f"'report-groups' entry #{i + 1} must be a YAML mapping (dict), got {type(entry).__name__}."
                )

            paths = [p.strip() for p in entry["paths"]]

            name = str(entry["name"]).strip()
            baseline_paths_raw = entry["baseline-paths"] if "baseline-paths" in entry else None
            baseline_paths = [p.strip() for p in baseline_paths_raw] if baseline_paths_raw is not None else None

            thresholds_str = entry.get("thresholds", "")
            overall: Optional[float] = None
            changed: Optional[float] = None
            per_file: Optional[float] = None
            if thresholds_str:
                parts = str(thresholds_str).split("*")
                overall = float(parts[0]) if parts[0] else None
                changed = float(parts[1]) if parts[1] else None
                per_file = float(parts[2]) if parts[2] else None

            groups.append(ReportGroup(name, paths, overall, changed, per_file, baseline_paths))

        return groups

    @staticmethod
    def get_skip_unchanged() -> bool:
        """
        Get the skip unchanged from the action inputs.
        """
        return ActionInputs._get_strict_boolean_input(
            input_name=SKIP_UNCHANGED,
            default_value="false",
            display_name="skip-unchanged",
        )

    @staticmethod
    def get_evaluate_unchanged() -> bool:
        """Get whether unchanged reports should still be evaluated when skip-unchanged is enabled."""
        return ActionInputs._get_strict_boolean_input(
            input_name=EVALUATE_UNCHANGED,
            default_value="true",
            display_name="evaluate-unchanged",
        )

    @staticmethod
    def get_update_comment() -> bool:
        """
        Get the update comment from the action inputs.
        """
        return ActionInputs._get_strict_boolean_input(
            input_name=UPDATE_COMMENT,
            default_value="true",
            display_name="update-comment",
        )

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
        Supports comma- or newline-separated values:
        overall, changed-files-average, per-changed-file, fail-unchanged.
        """
        value = get_action_input(FAIL_ON_THRESHOLD, "overall,changed-files-average,per-changed-file").strip().lower()

        if value in {"true", "false"}:
            raise ValueError(
                "Boolean values for 'fail-on-threshold' are no longer supported. "
                "Use a comma- or newline-separated list of: "
                "overall, changed-files-average, per-changed-file, fail-unchanged. "
                "Use an empty string to disable threshold failure."
            )

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
        return ActionInputs._get_strict_boolean_input(
            input_name=DEBUG,
            default_value="false",
            display_name="debug",
        )

    @staticmethod
    def _get_strict_boolean_input(input_name: str, default_value: str, display_name: str) -> bool:
        """Parse a boolean action input and require literal true/false values."""
        raw_value = str(get_action_input(input_name, default_value)).strip().lower()
        if raw_value == "true":
            return True
        if raw_value == "false":
            return False
        raise ValueError(f"'{display_name}' must be a boolean ('true' or 'false').")

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
        baseline_paths = get_action_input(BASELINE_PATHS)

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

        seen_names: set[str] = set()
        for i, entry in enumerate(data):
            prefix = f"'report-groups' entry #{i + 1}"
            if not isinstance(entry, dict):
                errors.append(f"{prefix} must be a YAML mapping.")
                continue
            name_value = entry.get("name")
            if not isinstance(name_value, str) or not name_value.strip():
                errors.append(f"{prefix} must have a non-empty 'name'.")
            else:
                group_name = name_value.strip()
                if group_name in seen_names:
                    errors.append(f"{prefix} has duplicate 'name' value '{group_name}'.")
                seen_names.add(group_name)
            paths = entry.get("paths")
            if not paths or not isinstance(paths, list) or not all(isinstance(p, str) and p.strip() for p in paths):
                errors.append(f"{prefix} must have a non-empty 'paths' list of non-empty strings.")
            has_thresholds = "thresholds" in entry
            thresholds_str = entry.get("thresholds")
            if has_thresholds and (not isinstance(thresholds_str, str) or not thresholds_str.strip()):
                errors.append(
                    f"{prefix} 'thresholds' must be a non-empty string in format 'O*A*P' " "(e.g. '80*70*60')."
                )
            elif isinstance(thresholds_str, str):
                parts = thresholds_str.split("*")
                if len(parts) != 3:
                    errors.append(f"{prefix} 'thresholds' must be in format 'O*A*P' (e.g. '80*70*60').")
                else:
                    for label, v in zip(("overall", "changed-files-average", "changed-file"), parts):
                        if v and not _is_valid_threshold_float(v):
                            errors.append(f"{prefix} 'thresholds' {label} value '{v}' must be a float in [0, 100).")
            has_baseline_paths = "baseline-paths" in entry
            baseline_paths = entry.get("baseline-paths", [])
            if has_baseline_paths and baseline_paths is None:
                errors.append(f"{prefix} 'baseline-paths' must be a list.")
            elif baseline_paths is not None and not isinstance(baseline_paths, list):
                errors.append(f"{prefix} 'baseline-paths' must be a list.")
            elif baseline_paths is not None and not all(isinstance(p, str) and p.strip() for p in baseline_paths):
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
        return bool(re.match(token_pattern, token))

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
                "'global-thresholds' must be in the format 'overall*changed-files-average*changed-file'. "
                "Where overall is the minimum coverage overall, changed-files-average is the minimum average coverage "
                "of changed files and changed-file is the minimum coverage per changed file."
            )
        else:
            if global_thresholds.count("*") == 1:
                logger.warning(
                    "'global-thresholds' should be in the format 'overall*changed-files-average*changed-file'. "
                    "Adding default value for changed file threshold."
                )
                global_thresholds += "*0.0"
            parts = global_thresholds.split("*")
            if len(parts) != 3:
                errors.append(
                    "'global-thresholds' must be in the format 'overall*changed-files-average*changed-file' "
                    "with exactly three components."
                )
            else:
                if not is_float(parts[0]) or float(parts[0]) < 0 or float(parts[0]) >= 100:
                    errors.append("'global-thresholds' overall value must be a float between 0 and 100.")
                if not is_float(parts[1]) or float(parts[1]) < 0 or float(parts[1]) >= 100:
                    errors.append("'global-thresholds' changed-files-average value must be a float between 0 and 100.")
                if not is_float(parts[2]) or float(parts[2]) < 0 or float(parts[2]) >= 100:
                    errors.append("'global-thresholds' changed-file value must be a float between 0 and 100.")

        report_thresholds_default = ActionInputs.get_report_thresholds_default(raw=True)
        if not isinstance(report_thresholds_default, str):
            errors.append("'report-thresholds-default' must be a string or not defined.")
        elif "*" not in report_thresholds_default:
            errors.append(
                "'report-thresholds-default' must be in the format 'overall*changed-files-average*per-changed-file'."
            )
        else:
            if report_thresholds_default.count("*") == 1:
                logger.warning(
                    "'report-thresholds-default' should be in the format "
                    "'overall*changed-files-average*per-changed-file'. "
                    "Adding default value for per-changed-file threshold."
                )
                report_thresholds_default += "*0.0"
            rtd_parts = report_thresholds_default.split("*")
            if len(rtd_parts) != 3:
                errors.append(
                    "'report-thresholds-default' must be in the format 'overall*changed-files-average*per-changed-file' "
                    "with exactly three components."
                )
            else:
                if not is_float(rtd_parts[0]) or float(rtd_parts[0]) < 0 or float(rtd_parts[0]) >= 100:
                    errors.append("'report-thresholds-default' overall value must be a float between 0 and 100.")
                if not is_float(rtd_parts[1]) or float(rtd_parts[1]) < 0 or float(rtd_parts[1]) >= 100:
                    errors.append(
                        "'report-thresholds-default' changed-files-average value must be a float between 0 and 100."
                    )
                if not is_float(rtd_parts[2]) or float(rtd_parts[2]) < 0 or float(rtd_parts[2]) >= 100:
                    errors.append(
                        "'report-thresholds-default' per-changed-file value must be a float between 0 and 100."
                    )

        metric = ActionInputs.get_metric()
        if not isinstance(metric, str) or metric not in MetricTypeEnum:
            errors.append(
                "'metric' must be a string from these options: 'instruction', "
                "'line', 'branch', 'complexity', 'method', 'class'."
            )

        comment_level = ActionInputs.get_comment_level()
        if not isinstance(comment_level, str) or comment_level not in CommentLevelEnum:
            errors.append(
                "'comment-level' must be a string from these options: "
                "'none', 'minimal', 'full', 'changed', 'failed', 'failed-or-changed'."
            )

        errors.extend(ActionInputs.validate_report_groups(report_groups_raw))

        skip_unchanged: Optional[bool] = None
        try:
            skip_unchanged = ActionInputs.get_skip_unchanged()
        except ValueError as e:
            errors.append(str(e))

        evaluate_unchanged: Optional[bool] = None
        try:
            evaluate_unchanged = ActionInputs.get_evaluate_unchanged()
        except ValueError as e:
            errors.append(str(e))

        update_comment: Optional[bool] = None
        try:
            update_comment = ActionInputs.get_update_comment()
        except ValueError as e:
            errors.append(str(e))

        pass_symbol = ActionInputs.get_pass_symbol()
        if not isinstance(pass_symbol, str) or not pass_symbol.strip() or len(pass_symbol) < 1:
            errors.append("'pass-symbol' must be a non-empty string and have a length from 1.")

        fail_symbol = ActionInputs.get_fail_symbol()
        if not isinstance(fail_symbol, str) or not fail_symbol.strip() or len(fail_symbol) < 1:
            errors.append("'fail-symbol' must be a non-empty string and have a length from 1.")

        fail_on_threshold: list[str] = []
        try:
            fail_on_threshold = ActionInputs.get_fail_on_threshold()
        except ValueError as e:
            errors.append(str(e))

        debug: Optional[bool] = None
        try:
            debug = ActionInputs.get_debug()
        except ValueError as e:
            errors.append(str(e))

        ActionInputs._log_configuration(
            report_groups_raw=report_groups_raw,
            skip_unchanged=skip_unchanged,
            evaluate_unchanged=evaluate_unchanged,
            update_comment=update_comment,
            fail_on_threshold=fail_on_threshold,
            debug=debug,
        )

        # Log errors if any
        if errors:
            for error in errors:
                logger.error("%s", error)
            sys.exit(1)

        logger.info("Action inputs validated successfully.")

    @staticmethod
    def _log_configuration(
        *,
        report_groups_raw: str,
        skip_unchanged: Optional[bool],
        evaluate_unchanged: Optional[bool],
        update_comment: Optional[bool],
        fail_on_threshold: list[str],
        debug: Optional[bool],
    ) -> None:
        """Log all resolved configuration values. Do not add token to this method."""
        # Do not add token here — token must never appear in logs.
        logger.info(
            "[CONFIGURATION] Received input values:\n"
            "Paths: %s\n"
            "Exclude paths: %s\n"
            "Baseline paths: %s\n"
            "\n"
            "Global thresholds: overall=%s, avg_changed_files=%s, changed_file=%s\n"
            "Report thresholds default: %s\n"
            "\n"
            "Report groups: %s\n"
            "\n"
            "Metric: %s\n"
            "Title: %s\n"
            "Comment level: %s\n"
            "\n"
            "Skip unchanged: %s\n"
            "Evaluate unchanged: %s\n"
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
            ActionInputs.get_report_thresholds_default(raw=True),
            report_groups_raw,
            ActionInputs.get_metric(),
            ActionInputs.get_title(),
            ActionInputs.get_comment_level(),
            skip_unchanged,
            evaluate_unchanged,
            update_comment,
            fail_on_threshold if fail_on_threshold else [],
            debug,
            ActionInputs.get_pass_symbol(),
            ActionInputs.get_fail_symbol(),
        )

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
    def get_run_id() -> str:
        """
        Get the GitHub Actions run ID from environment variables.
        """
        return get_action_input(GITHUB_RUN_ID, prefix="")

    @staticmethod
    def get_run_started_at() -> str:
        """
        Get the ISO 8601 timestamp when the run started (GITHUB_RUN_STARTED_AT).
        """
        return get_action_input(GITHUB_RUN_STARTED_AT, prefix="")

    @staticmethod
    def get_action_ref() -> str:
        """
        Get the ref (tag/SHA) used to invoke this action (GITHUB_ACTION_REF).
        """
        return get_action_input(GITHUB_ACTION_REF, prefix="")

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
