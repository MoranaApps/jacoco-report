"""
A module for handling the inputs provided to the GH action.
"""

import logging
import os
import re
import sys
from collections.abc import Callable
from typing import Any, Literal, Optional, TypeVar, overload

import yaml

from jacoco_report.utils.constants import (
    TOKEN,
    PATHS,
    EXCLUDE_PATHS,
    GLOBAL_THRESHOLDS,
    DEFAULT_GLOBAL_THRESHOLDS,
    GLOBAL_OVERALL_SCOPE,
    DEFAULT_GLOBAL_OVERALL_SCOPE,
    GLOBAL_OVERALL_SCOPE_ALL,
    GLOBAL_OVERALL_SCOPE_GROUPS_ONLY,
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
    CA_BUNDLE,
    GITHUB_RUN_ID,
    GITHUB_ACTION_PATH,
)

from jacoco_report.model.report_group import ReportGroup
from jacoco_report.utils.enums import CommentLevelEnum, MetricTypeEnum, FailOnThresholdEnum
from jacoco_report.utils.gh_action import get_action_input
from jacoco_report.utils.github import GitHub

logger = logging.getLogger(__name__)

_T = TypeVar("_T")


# `<runner work dir>/_actions/<owner>/<repo>/<ref>`; the ref may contain `/`
_ACTION_PATH_REF_PATTERN = re.compile(r"/_actions/[^/]+/[^/]+/(.+?)/*$")


def _is_valid_threshold_float(value: str) -> bool:
    try:
        f = float(value)
        return 0.0 <= f <= 100.0
    except ValueError:
        return False


def _read_or_record(getter: Callable[[], _T], errors: list[str]) -> Optional[_T]:
    """Call an input getter; on ValueError record its message in `errors` and return None."""
    try:
        return getter()
    except ValueError as e:
        errors.append(str(e))
        return None


def _threshold_range_errors(input_label: str, parts: list[str], part_labels: tuple[str, ...]) -> list[str]:
    """Return one error per threshold part that is not a float in [0, 100], in part order."""
    return [
        f"'{input_label}' {label} value must be a float between 0 and 100 (inclusive)."
        for part, label in zip(parts, part_labels)
        if not _is_valid_threshold_float(part)
    ]


def _validate_report_group_name(prefix: str, entry: dict[str, Any], seen_names: set[str]) -> list[str]:
    name_value = entry.get("name")
    if not isinstance(name_value, str) or not name_value.strip():
        return [f"{prefix} must have a non-empty 'name'."]
    group_name = name_value.strip()
    errors: list[str] = []
    if group_name in seen_names:
        errors.append(f"{prefix} has duplicate 'name' value '{group_name}'.")
    seen_names.add(group_name)
    return errors


def _validate_report_group_paths(prefix: str, entry: dict[str, Any]) -> list[str]:
    paths = entry.get("paths")
    if not paths or not isinstance(paths, list) or not all(isinstance(p, str) and p.strip() for p in paths):
        return [f"{prefix} must have a non-empty 'paths' list of non-empty strings."]
    return []


def _validate_report_group_thresholds(prefix: str, entry: dict[str, Any]) -> list[str]:
    has_thresholds = "thresholds" in entry
    thresholds_str = entry.get("thresholds")
    if has_thresholds and (not isinstance(thresholds_str, str) or not thresholds_str.strip()):
        return [f"{prefix} 'thresholds' must be a non-empty string in format 'O*A*P' (e.g. '80*70*60')."]
    if not isinstance(thresholds_str, str):
        return []
    parts = thresholds_str.split("*")
    if len(parts) != 3:
        return [f"{prefix} 'thresholds' must be in format 'O*A*P' (e.g. '80*70*60')."]
    return [
        f"{prefix} 'thresholds' {label} value '{v}' must be a float in [0, 100]."
        for label, v in zip(("overall", "changed-files-average", "changed-file"), parts)
        if v and not _is_valid_threshold_float(v)
    ]


def _validate_report_group_baseline_paths(prefix: str, entry: dict[str, Any]) -> list[str]:
    baseline_paths = entry.get("baseline-paths", [])
    if baseline_paths is None or not isinstance(baseline_paths, list):
        return [f"{prefix} 'baseline-paths' must be a list."]
    if not all(isinstance(p, str) and p.strip() for p in baseline_paths):
        return [f"{prefix} 'baseline-paths' must be a list of non-empty strings."]
    return []


def _validate_report_group_entry(prefix: str, entry: object, seen_names: set[str]) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{prefix} must be a YAML mapping."]
    return [
        *_validate_report_group_name(prefix, entry, seen_names),
        *_validate_report_group_paths(prefix, entry),
        *_validate_report_group_thresholds(prefix, entry),
        *_validate_report_group_baseline_paths(prefix, entry),
    ]


def _parse_threshold_part(value: str, label: str) -> float:
    """Parse one `*`-delimited threshold part; an empty or non-numeric part becomes 0.0."""
    try:
        return float(value) if value else 0.0
    except ValueError:
        logger.warning("Cannot convert '%s' part ('%s') to float. Defaulting to 0.0.", label, value)
        return 0.0


def _parse_thresholds(
    value: str, default_value: str, input_label: str, part_labels: tuple[str, ...]
) -> tuple[float, ...]:
    """Parse a `*`-delimited threshold input into one float per entry of `part_labels`.

    An input without `*` is replaced by `default_value`; missing trailing parts default to 0.0.
    """
    if "*" not in value:
        logger.warning("'%s' input is not formatted correctly.", input_label)
        value = default_value

    parts = value.split("*")
    if len(parts) < len(part_labels):
        missing = part_labels[len(parts) :]
        logger.warning(
            "'%s' input is not formatted correctly. Adding default value for %s threshold.",
            input_label,
            ", ".join(missing),
        )
        parts += [""] * len(missing)

    return tuple(_parse_threshold_part(part, label) for part, label in zip(parts, part_labels))


# One getter and one validator per action input, by design: the class is kept whole rather than split.
class ActionInputs:  # pylint: disable=too-many-public-methods
    """
    A class representing the inputs provided to the GH action.
    """

    @staticmethod
    def get_token() -> str:
        """
        Get the GitHub token from the action inputs.
        The value is provided by GitHub environment variable and define by GitHub.
        """
        token = get_action_input(TOKEN)
        normalized = token.strip()
        if normalized.lower().startswith("bearer "):
            normalized = normalized[7:].strip()
        return normalized

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
    def get_global_thresholds(raw: Literal[False] = ...) -> tuple[float, float]: ...
    @staticmethod
    def get_global_thresholds(raw: bool = False) -> tuple[float, float] | str:
        """Return the global coverage thresholds as a tuple (overall, changed-files-average)."""
        cleaned = ActionInputs.__get_thresholds_input(GLOBAL_THRESHOLDS, DEFAULT_GLOBAL_THRESHOLDS)
        if raw:
            return cleaned

        overall, changed = _parse_thresholds(
            cleaned, DEFAULT_GLOBAL_THRESHOLDS, "global-thresholds", ("overall", "changed-files-average")
        )
        return overall, changed

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
        cleaned = ActionInputs.__get_thresholds_input(REPORT_THRESHOLDS_DEFAULT, DEFAULT_REPORT_THRESHOLDS_DEFAULT)
        if raw:
            return cleaned

        overall, changed, per_file = _parse_thresholds(
            cleaned,
            DEFAULT_REPORT_THRESHOLDS_DEFAULT,
            "report-thresholds-default",
            ("overall", "changed-files-average", "per-changed-file"),
        )
        return overall, changed, per_file

    @staticmethod
    def __get_thresholds_input(input_name: str, default_value: str) -> str:
        """Read a threshold input with surrounding whitespace and any trailing `#` comment removed."""
        return ActionInputs.__clean_from_comment(get_action_input(input_name, default_value).strip())

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
    def get_global_overall_scope() -> str:
        """
        Get the global-overall-scope input ('all' or 'groups-only').
        Controls which reports contribute to global overall coverage when report-groups is configured.
        'all' includes every report found by the top-level paths scan (default).
        'groups-only' restricts global overall to reports matched by a group path pattern.
        """
        return get_action_input(GLOBAL_OVERALL_SCOPE, DEFAULT_GLOBAL_OVERALL_SCOPE).strip().lower()

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
    def get_ca_bundle() -> str:
        """
        Get the ca-bundle path from the action inputs. An empty string means unset.
        """
        return get_action_input(CA_BUNDLE, "").strip()

    @staticmethod
    def validate_ca_bundle() -> list[str]:
        """
        Validate the ca-bundle input: when set, it must be an existing file.
        """
        ca_bundle = ActionInputs.get_ca_bundle()
        if ca_bundle and not os.path.isfile(ca_bundle):
            return [f"'ca-bundle' must be a path to an existing PEM file: '{ca_bundle}'."]
        return []

    @staticmethod
    def validate_report_groups(raw_input: str) -> list[str]:
        """
        Validate the report-groups YAML input string.
        """
        if not raw_input:
            return []
        try:
            data = yaml.safe_load(raw_input)
        except yaml.YAMLError as e:
            return [f"'report-groups' is not valid YAML: {e}"]

        if not isinstance(data, list):
            return ["'report-groups' must be a YAML list."]

        errors: list[str] = []
        seen_names: set[str] = set()
        for i, entry in enumerate(data):
            errors.extend(_validate_report_group_entry(f"'report-groups' entry #{i + 1}", entry, seen_names))
        return errors

    @staticmethod
    def _validate_token() -> list[str]:
        token = ActionInputs.get_token()
        if not isinstance(token, str) or not token.strip():
            return ["'token' must be a non-empty string."]
        return []

    @staticmethod
    def _validate_paths() -> list[str]:
        paths = ActionInputs.get_paths(raw=True)
        if paths is None:
            return ["'paths' must be defined."]
        if not isinstance(paths, str):
            return ["'paths' must be a list of strings."]
        return []

    @staticmethod
    def _validate_global_thresholds() -> list[str]:
        global_thresholds = ActionInputs.get_global_thresholds(raw=True)
        if not isinstance(global_thresholds, str):
            return ["'global-thresholds' must be a string or not defined."]
        if "*" not in global_thresholds:
            return [
                "'global-thresholds' must be in the format 'overall*changed-files-average'. "
                "Where overall is the minimum coverage overall and changed-files-average is the minimum average "
                "coverage of changed files."
            ]
        parts = global_thresholds.split("*")
        if len(parts) != 2:
            return [
                "'global-thresholds' must be in the format 'overall*changed-files-average' "
                "with exactly two components."
            ]
        return _threshold_range_errors("global-thresholds", parts, ("overall", "changed-files-average"))

    @staticmethod
    def _validate_report_thresholds_default() -> list[str]:
        report_thresholds_default = ActionInputs.get_report_thresholds_default(raw=True)
        if not isinstance(report_thresholds_default, str):
            return ["'report-thresholds-default' must be a string or not defined."]
        if "*" not in report_thresholds_default:
            return [
                "'report-thresholds-default' must be in the format 'overall*changed-files-average*per-changed-file'."
            ]
        if report_thresholds_default.count("*") == 1:
            logger.warning(
                "'report-thresholds-default' should be in the format "
                "'overall*changed-files-average*per-changed-file'. "
                "Adding default value for per-changed-file threshold."
            )
            report_thresholds_default += "*0.0"
        rtd_parts = report_thresholds_default.split("*")
        if len(rtd_parts) != 3:
            return [
                "'report-thresholds-default' must be in the format "
                "'overall*changed-files-average*per-changed-file' "
                "with exactly three components."
            ]
        return _threshold_range_errors(
            "report-thresholds-default", rtd_parts, ("overall", "changed-files-average", "per-changed-file")
        )

    @staticmethod
    def _validate_metric() -> list[str]:
        metric = ActionInputs.get_metric()
        if not isinstance(metric, str) or metric not in {m.value for m in MetricTypeEnum}:
            return [
                "'metric' must be a string from these options: "
                "'instruction', 'line', 'branch', 'complexity', 'method', 'class'."
            ]
        return []

    @staticmethod
    def _validate_comment_level() -> list[str]:
        comment_level = ActionInputs.get_comment_level()
        if not isinstance(comment_level, str) or comment_level not in {c.value for c in CommentLevelEnum}:
            return [
                "'comment-level' must be a string from these options: "
                "'none', 'minimal', 'full', 'changed', 'failed', 'failed-or-changed'."
            ]
        return []

    @staticmethod
    def _validate_global_overall_scope() -> list[str]:
        global_overall_scope = ActionInputs.get_global_overall_scope()
        if global_overall_scope not in (GLOBAL_OVERALL_SCOPE_ALL, GLOBAL_OVERALL_SCOPE_GROUPS_ONLY):
            return ["'global-overall-scope' must be 'all' or 'groups-only'."]
        return []

    @staticmethod
    def _validate_symbols() -> list[str]:
        errors: list[str] = []
        pass_symbol = ActionInputs.get_pass_symbol()
        if not isinstance(pass_symbol, str) or not pass_symbol.strip() or len(pass_symbol) < 1:
            errors.append("'pass-symbol' must be a non-empty string and have a length from 1.")
        fail_symbol = ActionInputs.get_fail_symbol()
        if not isinstance(fail_symbol, str) or not fail_symbol.strip() or len(fail_symbol) < 1:
            errors.append("'fail-symbol' must be a non-empty string and have a length from 1.")
        return errors

    @staticmethod
    def validate_inputs() -> None:
        """
        Validates the inputs provided for the GH action.
        """
        errors: list[str] = []
        errors.extend(ActionInputs._validate_token())
        errors.extend(ActionInputs._validate_paths())
        errors.extend(ActionInputs._validate_global_thresholds())
        errors.extend(ActionInputs._validate_report_thresholds_default())
        errors.extend(ActionInputs._validate_metric())
        errors.extend(ActionInputs._validate_comment_level())

        report_groups_raw: str = ActionInputs.get_report_groups(raw=True)
        errors.extend(ActionInputs.validate_report_groups(report_groups_raw))

        skip_unchanged = _read_or_record(ActionInputs.get_skip_unchanged, errors)
        evaluate_unchanged = _read_or_record(ActionInputs.get_evaluate_unchanged, errors)
        errors.extend(ActionInputs._validate_global_overall_scope())
        update_comment = _read_or_record(ActionInputs.get_update_comment, errors)
        errors.extend(ActionInputs._validate_symbols())
        fail_on_threshold = _read_or_record(ActionInputs.get_fail_on_threshold, errors) or []
        debug = _read_or_record(ActionInputs.get_debug, errors)
        errors.extend(ActionInputs.validate_ca_bundle())

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
            "CA bundle: %s\n"
            "\n"
            "Global thresholds: overall=%s, avg_changed_files=%s\n"
            "Global overall scope: %s\n"
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
            ActionInputs.get_ca_bundle(),
            ActionInputs.get_global_overall_threshold(),
            ActionInputs.get_global_changed_files_average_threshold(),
            ActionInputs.get_global_overall_scope(),
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
    def get_action_ref() -> str:
        """
        Get the ref (tag, SHA or branch) this action was invoked with, e.g. "v3".

        Parsed from GITHUB_ACTION_PATH (`.../_actions/<owner>/<repo>/<ref>`), because GITHUB_ACTION_REF is
        empty in composite action steps (actions/runner#2473). Returns "" when the path does not match,
        e.g. for a local `uses: ./` action whose path is the workspace.
        """
        match = _ACTION_PATH_REF_PATTERN.search(get_action_input(GITHUB_ACTION_PATH, prefix=""))
        return match.group(1) if match else ""

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
