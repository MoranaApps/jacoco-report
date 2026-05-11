import pytest

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.utils.enums import CommentLevelEnum, MetricTypeEnum, FailOnThresholdEnum
from jacoco_report.utils.github import GitHub

# Data-driven test cases
success_case = {
    "get_token": "ghp_abcdefghijklmnopqrstuvwxyZ1234567890",
    # "get_token": "github_pat_12345ABCDE67890FGHIJKL_12345ABCDE67890FGHIJKL12345ABCDE67890FGHIJKL123456789012345",
    "get_paths": "path1,path2",
    "get_exclude_paths": "path1,path2",
    "get_global_thresholds": "0.0*0.0*0.0",
    "get_global_overall_threshold": 80.0,
    "get_global_changed_files_average_threshold": 70.0,
    "get_global_changed_file_threshold": 25.0,
    "get_title": "Custom Title",
    "get_metric": "instruction",
    "get_comment_level": "full",
    "get_report_groups": "",
    "get_skip_unchanged": True,
    "get_update_comment": True,
    "get_pass_symbol": "**Passed**",
    "get_fail_symbol": "❗",
    "get_fail_on_threshold": True,
    "get_debug": True,
}


failure_cases = [
    ("get_token", "", "'token' must be a non-empty string."),
    ("get_token", "-1", "'token' must be a valid GitHub token."),
    ("get_token", 1, "'token' must be a non-empty string."),
    ("get_paths", None, "'paths' must be defined."),
    ("get_paths", 1, "'paths' must be a list of strings."),
    ("get_paths", "", "'paths' must be a non-empty list of strings."),
    ("get_global_thresholds", "x", "'global-thresholds' must be in the format 'overall*changed_files_average*changed_file'. Where overall is the minimum coverage overall, changed_files_average is the minimum average coverage of changed files and changed_file is the minimum coverage per changed file."),
    ("get_global_thresholds", "x*0*0", "'global-thresholds' overall value must be a float between 0 and 100."),
    ("get_global_thresholds", "0*x*0", "'global-thresholds' changed_files_average files value must be a float between 0 and 100."),
    ("get_global_thresholds", "0*0*x", "'global-thresholds' changed-file value must be a float between 0 and 100."),
    ("get_global_thresholds", "-1*0*0", "'global-thresholds' overall value must be a float between 0 and 100."),
    ("get_global_thresholds", "0*-1*0", "'global-thresholds' changed_files_average files value must be a float between 0 and 100."),
    ("get_global_thresholds", "0*0*-1", "'global-thresholds' changed-file value must be a float between 0 and 100."),
    ("get_global_thresholds", "101*0*0", "'global-thresholds' overall value must be a float between 0 and 100."),
    ("get_global_thresholds", "0*101*0", "'global-thresholds' changed_files_average files value must be a float between 0 and 100."),
    ("get_global_thresholds", "0*0*101", "'global-thresholds' changed-file value must be a float between 0 and 100."),
    ("get_global_thresholds", True, "'global-thresholds' must be a string or not defined."),
    ("get_metric", "", "'metric' must be a string from these options: 'instruction', 'line', 'branch', 'complexity', 'method', 'class'."),
    ("get_metric", 1, "'metric' must be a string from these options: 'instruction', 'line', 'branch', 'complexity', 'method', 'class'."),
    ("get_comment_level", "", "'comment-level' must be a string from these options: 'minimal', 'full'."),
    ("get_comment_level", 1, "'comment-level' must be a string from these options: 'minimal', 'full'."),
    ("get_report_groups", "not_a_list", "'report-groups' must be a YAML list."),
    ("get_report_groups", "- name: ''\n  paths: ['**']", "'report-groups' entry #1 must have a non-empty 'name'."),
    ("get_report_groups", "- name: group1\n  paths: []", "'report-groups' entry #1 must have a non-empty 'paths' list of non-empty strings."),
    ("get_report_groups", "- name: group1\n  paths: ['**']\n  thresholds: '80'", "'report-groups' entry #1 'thresholds' must be in format 'O*A*P' (e.g. '80*70*60')."),
    ("get_report_groups", "- name: group1\n  paths: ['**']\n  thresholds: 'x*70*60'", "'report-groups' entry #1 'thresholds' overall value 'x' must be a float in [0, 100)."),
    ("get_skip_unchanged", "", "'skip-unchanged' must be a boolean."),
    ("get_skip_unchanged", 1, "'skip-unchanged' must be a boolean."),
    ("get_update_comment", "", "'update-comment' must be a boolean."),
    ("get_update_comment", 1, "'update-comment' must be a boolean."),
    ("get_pass_symbol", "", "'pass-symbol' must be a non-empty string and have a length from 1."),
    ("get_pass_symbol", 1, "'pass-symbol' must be a non-empty string and have a length from 1."),
    ("get_fail_symbol", "", "'fail-symbol' must be a non-empty string and have a length from 1."),
    ("get_fail_symbol", 1, "'fail-symbol' must be a non-empty string and have a length from 1."),
    ("get_debug", "", "'debug' must be a boolean."),
]


def apply_mocks(case, mocker):
    patchers = []
    for key, value in case.items():
        patcher = mocker.patch(f"jacoco_report.action_inputs.ActionInputs.{key}", return_value=value)
        patcher.start()
        patchers.append(patcher)
    return patchers


def stop_mocks(patchers):
    for patcher in patchers:
        patcher.stop()


def test_validate_inputs_success(mocker):
    patchers = apply_mocks(success_case, mocker)
    try:
        ActionInputs.validate_inputs()
    finally:
        stop_mocks(patchers)


@pytest.mark.parametrize("method, value, expected_error", failure_cases)
def test_validate_inputs_failure(method, value, expected_error, mocker):
    case = success_case.copy()
    case[method] = value
    patchers = apply_mocks(case, mocker)
    try:
        mock_error = mocker.patch("jacoco_report.action_inputs.logger.error")
        mock_exit = mocker.patch("sys.exit")

        ActionInputs.validate_inputs()

        mock_error.assert_called_with(expected_error)
        mock_exit.assert_called_once_with(1)

    finally:
        stop_mocks(patchers)


def test_get_token(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="some_token")
    assert "some_token" == ActionInputs.get_token()


def test_get_paths(mocker):
    data = f"""
    test/path1
    test/path2
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert ["test/path1", "test/path2"] == ActionInputs.get_paths()


def test_get_paths_with_comment(mocker):
    data = f"""
    test/path1
    test/path2      # another comment
    # test/path3    
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert ["test/path1", "test/path2"] == ActionInputs.get_paths()


def test_get_paths_raw(mocker):
    data = f"""
    test/path1
    test/path2
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert data == ActionInputs.get_paths(raw=True)


def test_get_paths_none(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=None)
    assert [] == ActionInputs.get_paths()


def test_get_exclude_paths(mocker):
    data = f"""
    test/path1
    test/path2
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert ["test/path1", "test/path2"] == ActionInputs.get_exclude_paths()


def test_get_exclude_paths_with_comment(mocker):
    data = f"""
    test/path1
    test/path2      # another comment
    #test/path3    
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert ["test/path1", "test/path2"] == ActionInputs.get_exclude_paths()


def test_get_exclude_paths_raw(mocker):
    data = f"""
    test/path1
    test/path2
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert data == ActionInputs.get_exclude_paths(raw=True)


def test_get_global_overall_threshold(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="0")
    assert 0.0 == ActionInputs.get_global_overall_threshold()


def test_get_global_changed_files_average_threshold(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="0")
    assert 0.0 == ActionInputs.get_global_changed_files_average_threshold()


def test_get_global_changed_file_threshold(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="0")
    assert 0.0 == ActionInputs.get_global_changed_file_threshold()


failure_cases_modes = [
    ("", "JaCoCo Coverage Report"),
    ("Custom title", "Custom title"),
]

@pytest.mark.parametrize("input_title, expected_title", failure_cases_modes)
def test_get_title(input_title, expected_title, mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=input_title)

    assert expected_title == ActionInputs.get_title()


def test_get_comment_level(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="full")
    assert "full" == ActionInputs.get_comment_level()


def test_get_report_groups_empty(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="")
    assert [] == ActionInputs.get_report_groups()


def test_get_report_groups_valid_yaml(mocker):
    yaml_input = """
- name: backend
  paths:
    - backend/**/jacoco.xml
  thresholds: 80*70*60
"""
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=yaml_input)
    groups = ActionInputs.get_report_groups()
    assert len(groups) == 1
    assert groups[0].name == "backend"
    assert groups[0].paths == ["backend/**/jacoco.xml"]
    assert groups[0].min_coverage_overall == 80.0
    assert groups[0].min_coverage_changed_files == 70.0
    assert groups[0].min_coverage_per_changed_file == 60.0


def test_get_report_groups_raw(mocker):
    raw = "- name: g\n  paths: ['**']"
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=raw)
    assert raw == ActionInputs.get_report_groups(raw=True)


def test_validate_report_groups_valid(mocker):
    yaml_input = "- name: g\n  paths: ['**/jacoco.xml']"
    errors = ActionInputs.validate_report_groups(yaml_input)
    assert errors == []


def test_validate_report_groups_empty(mocker):
    assert ActionInputs.validate_report_groups("") == []


def test_validate_report_groups_not_list(mocker):
    errors = ActionInputs.validate_report_groups("not_a_list")
    assert "'report-groups' must be a YAML list." in errors


def test_validate_report_groups_missing_name(mocker):
    errors = ActionInputs.validate_report_groups("- name: ''\n  paths: ['**']")
    assert any("non-empty 'name'" in e for e in errors)


def test_validate_report_groups_missing_paths(mocker):
    errors = ActionInputs.validate_report_groups("- name: group1")
    assert any("non-empty 'paths'" in e for e in errors)


def test_validate_report_groups_whitespace_only_paths_item(mocker):
    errors = ActionInputs.validate_report_groups("- name: group1\n  paths: ['  ']")
    assert any("non-empty 'paths'" in e for e in errors)


def test_validate_report_groups_invalid_threshold_format(mocker):
    errors = ActionInputs.validate_report_groups("- name: g\n  paths: ['**']\n  thresholds: '80'")
    assert any("O*A*P" in e for e in errors)


def test_validate_report_groups_invalid_threshold_value(mocker):
    errors = ActionInputs.validate_report_groups("- name: g\n  paths: ['**']\n  thresholds: 'x*70*60'")
    assert any("overall value" in e and "[0, 100)" in e for e in errors)


def test_validate_report_groups_invalid_baseline_paths_item_type(mocker):
    errors = ActionInputs.validate_report_groups("- name: g\n  paths: ['**']\n  baseline-paths: [123]")
    assert any("baseline-paths" in e and "non-empty strings" in e for e in errors)


def test_validate_report_groups_invalid_baseline_paths_empty_item(mocker):
    errors = ActionInputs.validate_report_groups("- name: g\n  paths: ['**']\n  baseline-paths: ['']")
    assert any("baseline-paths" in e and "non-empty strings" in e for e in errors)


def test_validate_report_groups_invalid_baseline_paths_null(mocker):
    errors = ActionInputs.validate_report_groups("- name: g\n  paths: ['**']\n  baseline-paths: null")
    assert any("baseline-paths" in e and "must be a list" in e for e in errors)


def test_get_skip_unchanged_true(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="true")
    assert ActionInputs.get_skip_unchanged()


def test_get_skip_unchanged_false(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    assert not ActionInputs.get_skip_unchanged()


def test_get_update_comment_true(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="true")
    assert True == ActionInputs.get_update_comment()


def test_get_update_comment_false(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    assert False == ActionInputs.get_update_comment()


def test_get_pass_symbol(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="P")
    assert "P" == ActionInputs.get_pass_symbol()


def test_get_fail_symbol(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="F")
    assert "F" == ActionInputs.get_fail_symbol()


def test_get_fail_on_threshold_true(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="true")
    expected = [FailOnThresholdEnum.OVERALL, FailOnThresholdEnum.CHANGED_FILES_AVERAGE, FailOnThresholdEnum.PER_CHANGED_FILE]
    assert expected == ActionInputs.get_fail_on_threshold()


def test_get_fail_on_threshold_false(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    assert ActionInputs.get_fail_on_threshold() == []


def test_get_fail_on_threshold_overall(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="overall")
    assert ActionInputs.get_fail_on_threshold() == [FailOnThresholdEnum.OVERALL]


def test_get_fail_on_threshold_overall_changed_average(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="overall\nchanged-files-average")
    assert ActionInputs.get_fail_on_threshold() == [FailOnThresholdEnum.OVERALL, FailOnThresholdEnum.CHANGED_FILES_AVERAGE]


def test_get_fail_on_threshold_invalid_format(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="not supported")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_fail_on_threshold()

    assert "Unsupported threshold levels: not supported" in str(exc_info.value)


def test_get_debug_true(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="true")
    assert True == ActionInputs.get_debug()


def test_get_debug_false(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    assert False == ActionInputs.get_debug()


def test_get_baseline_paths(mocker):
    data = f"""
    test/path1
    test/path2
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert ["test/path1", "test/path2"] == ActionInputs.get_baseline_paths()


def test_get_baseline_paths_with_comment(mocker):
    data = f"""
    test/path1
    test/path2      # another comment
    #test/path3
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert ["test/path1", "test/path2"] == ActionInputs.get_baseline_paths()


def test_get_baseline_paths_raw(mocker):
    data = f"""
    test/path1
    test/path2
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=data)
    assert data == ActionInputs.get_baseline_paths(raw=True)

def test_get_pr_number(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="123")
    gh = mocker.Mock(spec=GitHub)
    assert ActionInputs.get_pr_number(gh) == 123

    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=None)
    gh.get_pr_number.return_value = 456
    assert ActionInputs.get_pr_number(gh) == 456

    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=None)
    gh.get_pr_number.return_value = None
    mock_logger = mocker.patch("jacoco_report.action_inputs.logger")
    assert ActionInputs.get_pr_number(gh) is None
    mock_logger.error.assert_called_once_with("The PR number not detected.")

def test_get_metric(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="branch")
    assert ActionInputs.get_metric() == "branch"

def test_get_event_name(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="push")
    assert ActionInputs.get_event_name() == "push"


# --- Issue 6: whitespace-only paths ---
def test_validate_inputs_paths_whitespace_only_requires_error_without_groups(mocker):
    case = success_case.copy()
    case["get_paths"] = "  \n  "
    case["get_report_groups"] = ""

    patchers = apply_mocks(case, mocker)
    try:
        mock_error = mocker.patch("jacoco_report.action_inputs.logger.error")
        mock_exit = mocker.patch("sys.exit")
        mocker.patch(
            "jacoco_report.action_inputs.ActionInputs.get_paths",
            side_effect=lambda raw=False: "  \n  " if raw else [],
        )

        ActionInputs.validate_inputs()

        mock_error.assert_any_call("'paths' must be a non-empty list of strings.")
        mock_exit.assert_called_once_with(1)
    finally:
        stop_mocks(patchers)


def test_validate_inputs_paths_whitespace_only_allowed_with_groups(mocker):
    case = success_case.copy()
    case["get_paths"] = "  \n  "
    case["get_report_groups"] = "- name: g1\n  paths: ['**']"

    patchers = apply_mocks(case, mocker)
    try:
        mock_exit = mocker.patch("sys.exit")
        mocker.patch(
            "jacoco_report.action_inputs.ActionInputs.get_paths",
            side_effect=lambda raw=False: "  \n  " if raw else [],
        )

        ActionInputs.validate_inputs()

        mock_exit.assert_not_called()
    finally:
        stop_mocks(patchers)


# --- Issue 7: yaml.YAMLError handling ---
def test_get_report_groups_yaml_syntax_error_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="invalid: yaml: [")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "is not valid YAML" in str(exc_info.value)


# --- Issue 8: entry validation in get_report_groups ---
def test_get_report_groups_entry_not_mapping_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value='["not-a-dict"]')

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "mapping" in str(exc_info.value).lower() or "dict" in str(exc_info.value).lower()


def test_get_report_groups_missing_name_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="- paths: ['**']")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "name" in str(exc_info.value).lower()


def test_get_report_groups_missing_paths_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="- name: g1")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "paths" in str(exc_info.value).lower()


def test_get_report_groups_paths_not_list_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="- name: g1\n  paths: single-string")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "list" in str(exc_info.value).lower()


def test_get_report_groups_empty_paths_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="- name: g1\n  paths: []")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "non-empty" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()


def test_get_report_groups_invalid_threshold_format_raises_value_error(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="- name: g1\n  paths: ['**']\n  thresholds: '80'")

    with pytest.raises(ValueError) as exc_info:
        ActionInputs.get_report_groups(raw=False)

    assert "thresholds" in str(exc_info.value).lower()
    assert "o*a*p" in str(exc_info.value).lower()


failure_cases_defaults = [
    # ("get_token", ""),    # There are no defaults for token, it must be provided.
    # ("get_paths", ""),    # There are no defaults for paths, it must be provided.
    ("get_exclude_paths", []),
    ("get_title", "JaCoCo Coverage Report"),
    ("get_metric", MetricTypeEnum.INSTRUCTION),
    ("get_comment_level", CommentLevelEnum.FULL),
    ("get_report_groups", []),
    ("get_skip_unchanged", False),
    ("get_update_comment", True),
    ("get_pass_symbol", "✅"),
    ("get_fail_symbol", "❌"),
    ("get_fail_on_threshold", [FailOnThresholdEnum.OVERALL, FailOnThresholdEnum.CHANGED_FILES_AVERAGE, FailOnThresholdEnum.PER_CHANGED_FILE]),
    ("get_debug", False),
    ("get_global_thresholds", (0.0, 0.0, 0.0)),
    ("get_global_overall_threshold", 0.0),
    ("get_global_changed_files_average_threshold", 0.0),
    ("get_global_changed_file_threshold", 0.0),
]

@pytest.mark.parametrize("method, expected_value", failure_cases_defaults)
def test_validate_inputs_default(method, expected_value, mocker):
    case = success_case.copy()
    case.pop(method)

    if method in ("get_global_overall_threshold", "get_global_changed_files_average_threshold", "get_global_changed_file_threshold"):
        case["get_global_thresholds"] = (0.0, 0.0, 0.0)

    patchers = apply_mocks(case, mocker)
    try:
        # ActionInputs.validate_inputs()
        assert getattr(ActionInputs, method)() == expected_value
    finally:
        stop_mocks(patchers)


def test_validate_inputs_allows_empty_paths_when_report_groups_configured(mocker):
    case = success_case.copy()
    case["get_paths"] = ""
    case["get_report_groups"] = "- name: group1\n  paths: ['**/jacoco.xml']"

    patchers = apply_mocks(case, mocker)
    try:
        mock_exit = mocker.patch("sys.exit")
        ActionInputs.validate_inputs()
        mock_exit.assert_not_called()
    finally:
        stop_mocks(patchers)


def test_validate_inputs_requires_paths_when_report_groups_not_configured(mocker):
    case = success_case.copy()
    case["get_paths"] = ""
    case["get_report_groups"] = ""

    patchers = apply_mocks(case, mocker)
    try:
        mock_error = mocker.patch("jacoco_report.action_inputs.logger.error")
        mock_exit = mocker.patch("sys.exit")
        ActionInputs.validate_inputs()

        mock_error.assert_any_call("'paths' must be a non-empty list of strings.")
        mock_exit.assert_called_once_with(1)
    finally:
        stop_mocks(patchers)


def test_validate_inputs_requires_paths_when_report_groups_is_empty_yaml_list(mocker):
    case = success_case.copy()
    case["get_paths"] = ""
    case["get_report_groups"] = "[]"

    patchers = apply_mocks(case, mocker)
    try:
        mock_error = mocker.patch("jacoco_report.action_inputs.logger.error")
        mock_exit = mocker.patch("sys.exit")
        ActionInputs.validate_inputs()

        mock_error.assert_any_call("'paths' must be a non-empty list of strings.")
        mock_exit.assert_called_once_with(1)
    finally:
        stop_mocks(patchers)
