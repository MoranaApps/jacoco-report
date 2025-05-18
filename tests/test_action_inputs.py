import pytest

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.utils.enums import CommentModeEnum
from jacoco_report.utils.github import GitHub

# Data-driven test cases
success_case = {
    "get_token": "ghp_abcdefghijklmnopqrstuvwxyZ1234567890",
    # "get_token": "github_pat_12345ABCDE67890FGHIJKL_12345ABCDE67890FGHIJKL12345ABCDE67890FGHIJKL123456789012345",
    "get_paths": "path1,path2",
    "get_exclude_paths": "path1,path2",
    "get_min_coverage_overall": 80.0,
    "get_min_coverage_changed_files": 70.0,
    "get_min_coverage_per_changed_file": 25.0,
    "get_title": "Custom Title",
    "get_metric": "instruction",
    "get_sensitivity": "detail",
    "get_comment_mode": "single",
    "get_modules": "module-a:context/module_a,module-b:module_b",
    "get_modules_thresholds": "module-a:80**,module-b:*70*",
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
    ("get_min_coverage_overall", "x", "'min-coverage-overall' must be a float between 0 and 100."),
    ("get_min_coverage_overall", True, "'min-coverage-overall' must be a float between 0 and 100."),
    ("get_min_coverage_overall", -1, "'min-coverage-overall' must be a float between 0 and 100."),
    ("get_min_coverage_overall", 100, "'min-coverage-overall' must be a float between 0 and 100."),
    ("get_min_coverage_changed_files", "x", "'min-coverage-changed-files' must be a float between 0 and 100."),
    ("get_min_coverage_changed_files", True, "'min-coverage-changed-files' must be a float between 0 and 100."),
    ("get_min_coverage_changed_files", -1, "'min-coverage-changed-files' must be a float between 0 and 100."),
    ("get_min_coverage_changed_files", 100, "'min-coverage-changed-files' must be a float between 0 and 100."),
    ("get_min_coverage_per_changed_file", "x", "'min-coverage-per-changed-file' must be a float between 0 and 100."),
    ("get_min_coverage_per_changed_file", True, "'min-coverage-per-changed-file' must be a float between 0 and 100."),
    ("get_min_coverage_per_changed_file", -1, "'min-coverage-per-changed-file' must be a float between 0 and 100."),
    ("get_min_coverage_per_changed_file", 100, "'min-coverage-per-changed-file' must be a float between 0 and 100."),
    ("get_metric", "", "'metric' must be a string from these options: 'instruction', 'line', 'branch', 'complexity', 'method', 'class'."),
    ("get_metric", 1, "'metric' must be a string from these options: 'instruction', 'line', 'branch', 'complexity', 'method', 'class'."),
    ("get_sensitivity", "", "'sensitivity' must be a string from these options: 'minimal', 'summary', 'detail'."),
    ("get_sensitivity", 1, "'sensitivity' must be a string from these options: 'minimal', 'summary', 'detail'."),
    ("get_comment_mode", "", "'comment-mode' must be a string from these options: 'single', 'multi', 'module'."),
    ("get_comment_mode", 1, "'comment-mode' must be a string from these options: 'single', 'multi', 'module'."),
    ("get_modules", 1, "'modules' must be a string or not defined."),
    ("get_modules", "abcd", "'modules' must be a list of strings in format 'module:relative_path'."),
    ("get_modules", "module-a:context/module_a,module-b", "'module':'module-b' must be in the format 'module:module_path'. Where module_path is relative from root of project. Module value: module-b"),
    ("get_modules", "module-a: context/module_a,:module_b", "Module with value:'module_b' must have a non-empty name."),
    ("get_modules", "module-a:context/module_a,module_b:", "Module with 'name':'module_b' must have a non-empty path."),
    ("get_modules", "module-a:context/module_a,mo*dule:path", "'module_name':'mo*dule' must be alphanumeric with allowed (/\\-_)."),
    ("get_modules", "module-a:context/module_a,module:pa&th", "'module_path':'pa&th' must be alphanumeric with allowed (/\\-_)."),
    ("get_modules", "module-a:context/module_a,module-b:module_b:c", "'module':'module-b:module_b:c' must be in the format 'module:module_path'. Where module_path is relative from root of project. Module value: module-b:module_b:c"),
    ("get_modules_thresholds", 1, "'modules-thresholds' must be a string or not defined."),
    ("get_modules_thresholds", "ab", "'modules-thresholds' must be a list of strings in format 'module:overall*changed'."),
    ("get_modules_thresholds", "abcd", "'modules-thresholds' must be a list of strings in format 'module:overall*changed'."),
    ("get_modules_thresholds", "module-a: 80**,", "'module-threshold' must be a non-empty string."),
    ("get_modules_thresholds", "module-a: 80*", "'module-threshold':'80*' must contain two '*' to split overall, changed files and changed per file threshold."),
    ("get_modules_thresholds", "module-a:80**,module-b", "'module-threshold':'module-b' must be in the format 'module:threshold'."),
    ("get_modules_thresholds", "module-a:80**,:80.0**", "Module threshold with value:'80.0**' must have a non-empty name."),
    ("get_modules_thresholds", "module-a:80**,module-b:", "Module threshold with 'name':'module-b' must have a non-empty threshold."),
    ("get_modules_thresholds", "module-a:80**,module-b:80", "'module-threshold':'80' must contain two '*' to split overall, changed files and changed per file threshold."),
    ("get_modules_thresholds", "module-a:80**,module-b:True**", "'module-threshold' overall value 'True' must be a float or None."),
    ("get_modules_thresholds", "module-a:80**,module-b:*True*", "'module-threshold' changed files value 'True' must be a float or None."),
    ("get_modules_thresholds", "module-a:80**,module-b:**True", "'module-threshold' changed per file value 'True' must be a float or None."),
    ("get_modules_thresholds", "module-a:80**,module-b:*80*:9", "'module-threshold':'module-b:*80*:9' must be in the format 'module:threshold'."),
    ("get_modules_thresholds", "module-a:80**,module-b:*80*:9", "'module-threshold':'module-b:*80*:9' must be in the format 'module:threshold'."),
    ("get_skip_unchanged", "", "'skip-unchanged' must be a boolean."),
    ("get_skip_unchanged", 1, "'skip-unchanged' must be a boolean."),
    ("get_update_comment", "", "'update-comment' must be a boolean."),
    ("get_update_comment", 1, "'update-comment' must be a boolean."),
    ("get_pass_symbol", "", "'pass-symbol' must be a non-empty string and have a length from 1."),
    ("get_pass_symbol", 1, "'pass-symbol' must be a non-empty string and have a length from 1."),
    ("get_fail_symbol", "", "'fail-symbol' must be a non-empty string and have a length from 1."),
    ("get_fail_symbol", 1, "'fail-symbol' must be a non-empty string and have a length from 1."),
    ("get_fail_on_threshold", "", "'fail-on-threshold' must be a boolean."),
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
    test/path2
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
    test/path2
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


def test_get_min_coverage_overall(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="0")
    assert 0.0 == ActionInputs.get_min_coverage_overall()


def test_get_min_coverage_changed_files(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="0")
    assert 0.0 == ActionInputs.get_min_coverage_changed_files()


def test_get_min_coverage_per_changed_file(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="0")
    assert 0.0 == ActionInputs.get_min_coverage_per_changed_file()


failure_cases = [
    ("", CommentModeEnum.SINGLE, None, "JaCoCo Coverage Report"),
    ("", CommentModeEnum.SINGLE, "Report Name", "JaCoCo Coverage Report"),
    ("", CommentModeEnum.MULTI, None, "Report: Unknown Report Name"),
    ("", CommentModeEnum.MULTI, "Report Name", "Report: Report Name"),
    ("", CommentModeEnum.MODULE, None, "Module: Unknown Report Name"),
    ("", CommentModeEnum.MODULE, "Report Name", "Module: Report Name"),
    ("Custom title", CommentModeEnum.SINGLE, None, "Custom title"),
    ("Custom title", CommentModeEnum.SINGLE, "Report Name", "Custom title"),
    ("Custom title ", CommentModeEnum.MULTI, None, "Custom title Unknown Report Name"),
    ("Custom title ", CommentModeEnum.MULTI, "Report Name", "Custom title Report Name"),
    ("Custom title ", CommentModeEnum.MODULE, None, "Custom title Unknown Report Name"),
    ("Custom title ", CommentModeEnum.MODULE, "Report Name", "Custom title Report Name"),
]

@pytest.mark.parametrize("input_title, comment_mode, report_name, expected_title", failure_cases)
def test_get_title(input_title, comment_mode, report_name, expected_title, mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=input_title)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_comment_mode", return_value=comment_mode)

    assert expected_title == ActionInputs.get_title(report_name)


def test_get_comment_template(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="detailed")
    assert "detailed" == ActionInputs.get_sensitivity()


def test_get_comment_mode(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="single")
    assert "single" == ActionInputs.get_comment_mode()


def test_get_modules_no_spaces(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="module-a:context/module_a,module-b:module_b")
    assert {"module-a": "context/module_a", "module-b": "module_b"} == ActionInputs.get_modules()


def test_get_modules_with_spaces(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="module-a: context/module_a,module-b: module_b")
    assert {"module-a": "context/module_a", "module-b": "module_b"} == ActionInputs.get_modules()


def test_get_modules_with_commented_line(mocker):
    input_data = """module-a: context/module_a
    # module-b: module_b
    # module-c: context/module_c
    module-d: context/module_d
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=input_data)
    assert {"module-a": "context/module_a", "module-d": "context/module_d"} == ActionInputs.get_modules()


def test_get_modules_raw(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="  module-a:context/module_a,module-b:module_b")
    assert "module-a:context/module_a,module-b:module_b" == ActionInputs.get_modules(raw=True)


def test_get_modules_thresholds_no_spaces(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_overall", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_changed_files", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_per_changed_file", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="module-a:80**,module-b:*70*")
    assert {"module-a": (80.0, 0.0, 0.0), "module-b": (0.0, 70.0, 0.0)} == ActionInputs.get_modules_thresholds()


def test_get_modules_thresholds_with_spaces(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_overall", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_changed_files", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_per_changed_file", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="module-a: 80**,module-b: *70*")
    assert {"module-a": (80.0, 0.0, 0.0), "module-b": (0.0, 70.0, 0.0)} == ActionInputs.get_modules_thresholds()


def test_get_modules_thresholds_with_commented_line(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_overall", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_changed_files", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_min_coverage_per_changed_file", return_value=0.0)
    input_data = """module-a: 80**
    module-b: *70*
    #module-c: 90**
    # module-d: *100*
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=input_data)
    assert {"module-a": (80.0, 0.0, 0.0), "module-b": (0.0, 70.0, 0.0)} == ActionInputs.get_modules_thresholds()


def test_get_modules_thresholds_raw(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="  module-a:80*,module-b:  *70")
    assert "module-a:80*,module-b:  *70" == ActionInputs.get_modules_thresholds(raw=True)


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
    assert True == ActionInputs.get_fail_on_threshold()


def test_get_fail_on_threshold_false(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="false")
    assert False == ActionInputs.get_fail_on_threshold()


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
    test/path2
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
