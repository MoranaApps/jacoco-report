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
    ("get_modules", 1, "'modules' must be a string or not defined."),
    ("get_modules", "abcd", "'modules' must be a list of strings in format 'module:relative_path'."),
    ("get_modules", "module-a:context/module_a,module-b", "'module':'module-b' must be in the format 'module:module_path'. Where module_path is relative from root of project. Module value: module-b"),
    ("get_modules", "module-a: context/module_a,:module_b", "Module with value:'module_b' must have a non-empty name."),
    ("get_modules", "module-a:context/module_a,module_b:", "Module with 'name':'module_b' must have a non-empty path."),
    ("get_modules", "module-a:context/module_a,mo*dule:path", "'module_name':'mo*dule' must be alphanumeric with allowed (/\\-_)."),
    ("get_modules", "module-a:context/module_a,module:pa&th", "'module_path':'pa&th' must be alphanumeric with allowed (/\\-_)."),
    ("get_modules", "module-a:context/module_a,module-b:module_b:c", "'module':'module-b:module_b:c' must be in the format 'module:module_path'. Where module_path is relative from root of project. Module value: module-b:module_b:c"),
    # TODO - uncomment when new format of modules thresholds will be supported
    # ("get_modules_thresholds", 1, "'modules-thresholds' must be a string or not defined."),
    # ("get_modules_thresholds", "ab", "'modules-thresholds' must be a list of strings in format 'module:overall*changed'."),
    # ("get_modules_thresholds", "abcd", "'modules-thresholds' must be a list of strings in format 'module:overall*changed'."),
    # ("get_modules_thresholds", "module-a: 80*", "'module-threshold':'80*' must contain two '*' to split overall, changed files and changed per file threshold."),
    # ("get_modules_thresholds", "module-a:80**,module-b", "'module-threshold':'module-b' must be in the format 'module:threshold'."),
    # ("get_modules_thresholds", "module-a:80**,:80.0**", "Module threshold with value:'80.0**' must have a non-empty name."),
    # ("get_modules_thresholds", "module-a:80**,module-b:", "Module threshold with 'name':'module-b' must have a non-empty threshold."),
    # ("get_modules_thresholds", "module-a:80**,module-b:80", "'module-threshold':'80' must contain two '*' to split overall, changed files and changed per file threshold."),
    # ("get_modules_thresholds", "module-a:80**,module-b:True**", "'module-threshold' overall value 'True' must be a float or None."),
    # ("get_modules_thresholds", "module-a:80**,module-b:*True*", "'module-threshold' changed files value 'True' must be a float or None."),
    # ("get_modules_thresholds", "module-a:80**,module-b:**True", "'module-threshold' changed per file value 'True' must be a float or None."),
    # ("get_modules_thresholds", "module-a:80**,module-b:*80*:9", "'module-threshold':'module-b:*80*:9' must be in the format 'module:threshold'."),
    # ("get_modules_thresholds", "module-a:80**,module-b:*80*:9", "'module-threshold':'module-b:*80*:9' must be in the format 'module:threshold'."),
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
    module-d: context/module_d      # another comment
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=input_data)
    assert {"module-a": "context/module_a", "module-d": "context/module_d"} == ActionInputs.get_modules()


def test_get_modules_raw(mocker):
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="  module-a:context/module_a,module-b:module_b")
    assert "module-a:context/module_a,module-b:module_b" == ActionInputs.get_modules(raw=True)


def test_get_modules_thresholds_no_spaces(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_file_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="module-a:80**,module-b:*70*")
    assert {"module-a": (80.0, 0.0, 0.0), "module-b": (0.0, 70.0, 0.0)} == ActionInputs.get_modules_thresholds()


def test_get_modules_thresholds_with_spaces(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_file_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value="module-a: 80**,module-b: *70*")
    assert {"module-a": (80.0, 0.0, 0.0), "module-b": (0.0, 70.0, 0.0)} == ActionInputs.get_modules_thresholds()


def test_get_modules_thresholds_with_commented_line(mocker):
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_files_average_threshold", return_value=0.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_file_threshold", return_value=0.0)
    input_data = """module-a: 80**
    module-b: *70*
    #module-c: 90**
    # module-d: *100*
    module-e: *100*     # another comment 
    """
    mocker.patch("jacoco_report.action_inputs.get_action_input", return_value=input_data)
    assert ActionInputs.get_modules_thresholds() == {"module-a": (80.0, 0.0, 0.0), "module-b": (0.0, 70.0, 0.0), "module-e": (0.0, 100.0, 0.0)}


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


failure_cases_defaults = [
    # ("get_token", ""),    # There are no defaults for token, it must be provided.
    # ("get_paths", ""),    # There are no defaults for paths, it must be provided.
    ("get_exclude_paths", []),
    ("get_title", "JaCoCo Coverage Report"),
    ("get_metric", MetricTypeEnum.INSTRUCTION),
    ("get_comment_level", CommentLevelEnum.FULL),
    ("get_modules", {}),
    ("get_modules_thresholds", {}),
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
