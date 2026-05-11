from jacoco_report.model.report_group import ReportGroup


def test_initialization_required_fields():
    group = ReportGroup(name="my-group", paths=["**/jacoco.xml"])

    assert group.name == "my-group"
    assert group.paths == ["**/jacoco.xml"]
    assert group.min_coverage_overall is None
    assert group.min_coverage_changed_files is None
    assert group.min_coverage_per_changed_file is None
    assert group.baseline_paths == []


def test_initialization_all_fields():
    group = ReportGroup(
        name="backend",
        paths=["backend/**/jacoco.xml"],
        min_coverage_overall=75.0,
        min_coverage_changed_files=80.0,
        min_coverage_per_changed_file=70.0,
        baseline_paths=["baseline/jacoco.xml"],
    )

    assert group.name == "backend"
    assert group.paths == ["backend/**/jacoco.xml"]
    assert group.min_coverage_overall == 75.0
    assert group.min_coverage_changed_files == 80.0
    assert group.min_coverage_per_changed_file == 70.0
    assert group.baseline_paths == ["baseline/jacoco.xml"]


def test_baseline_paths_defaults_to_empty_list():
    group = ReportGroup(name="g", paths=["**"], baseline_paths=None)
    assert group.baseline_paths == []
