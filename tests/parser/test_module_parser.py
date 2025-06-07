from jacoco_report.parser.module_parser import ModuleParser
from jacoco_report.model.module import Module

# parse

def test_parse():
    modules = {
        "module1": "path/to/module1",
        "module2": "path/to/module2"
    }
    modules_thresholds = {
        "module1": (75.0, 80.0, 80.0),
        "module2": (85.0, 90.0, 80.0)
    }

    parsed_modules = ModuleParser.parse(modules, modules_thresholds)

    assert len(parsed_modules) == 2
    assert isinstance(parsed_modules["module1"], Module)
    assert parsed_modules["module1"].name == "module1"
    assert parsed_modules["module1"].min_coverage_overall == 75.0
    assert parsed_modules["module1"].min_coverage_changed_files == 80.0
    assert parsed_modules["module1"].min_coverage_per_changed_file == 80.0
    assert isinstance(parsed_modules["module2"], Module)
    assert parsed_modules["module2"].name == "module2"
    assert parsed_modules["module2"].min_coverage_overall == 85.0
    assert parsed_modules["module2"].min_coverage_changed_files == 90.0
    assert parsed_modules["module2"].min_coverage_per_changed_file == 80.0


def test_parse_missing_thresholds(mocker):
    modules = {
        "module1": "path/to/module1",
        "module2": "path/to/module2"
    }
    modules_thresholds = {
        "module1": (75.0, 80.0, 80.0)
    }

    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_overall_threshold", return_value=50.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_avg_changed_files_threshold", return_value=60.0)
    mocker.patch("jacoco_report.action_inputs.ActionInputs.get_global_changed_file_threshold", return_value=60.0)

    parsed_modules = ModuleParser.parse(modules, modules_thresholds)

    assert len(parsed_modules) == 2
    assert isinstance(parsed_modules["module1"], Module)
    assert parsed_modules["module1"].name == "module1"
    assert parsed_modules["module1"].min_coverage_overall == 75.0
    assert parsed_modules["module1"].min_coverage_changed_files == 80.0
    assert parsed_modules["module1"].min_coverage_per_changed_file == 80.0
    assert isinstance(parsed_modules["module2"], Module)
    assert parsed_modules["module2"].name == "module2"
    assert parsed_modules["module2"].min_coverage_overall == 50.0
    assert parsed_modules["module2"].min_coverage_changed_files == 60.0
    assert parsed_modules["module2"].min_coverage_per_changed_file == 60.0
