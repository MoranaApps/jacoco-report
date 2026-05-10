from jacoco_report.model.module import Module

# __init__

def test_initialization():
    module = Module(name="module_name", unique_path="some/path", min_coverage_overall=75.0,
                    min_coverage_changed_files=80.0, min_coverage_changed_per_file=80.0)

    assert module.name == "module_name"
    assert module.min_coverage_overall == 75.0
    assert module.min_coverage_changed_files == 80.0
    assert module.min_coverage_per_changed_file == 80.0
    assert module.root_path == "some/path"
