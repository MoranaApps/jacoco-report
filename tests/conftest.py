import pytest
from typing import Callable, Optional

from pytest_mock import MockerFixture

from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.model.counter import Counter
from jacoco_report.model.coverage import Coverage
from jacoco_report.model.evaluated_report_coverage import EvaluatedReportCoverage
from jacoco_report.model.file_coverage import FileCoverage
from jacoco_report.model.module import Module
from jacoco_report.model.report_file_coverage import ReportFileCoverage
from jacoco_report.utils.github import GitHub


@pytest.fixture
def mock_logging_setup(mocker: MockerFixture):
    mock_log_config = mocker.patch("logging.basicConfig")
    yield mock_log_config


@pytest.fixture
def github(mocker: MockerFixture) -> GitHub:
    mocker.patch("os.getenv", return_value="fake_repo")
    return GitHub("fake_token")


@pytest.fixture
def jacoco_report() -> JaCoCoReport:
    return JaCoCoReport()


@pytest.fixture
def make_counter() -> Callable[..., Counter]:
    def factory(missed: int = 0, covered: int = 10) -> Counter:
        return Counter(missed=missed, covered=covered)

    return factory


@pytest.fixture
def make_coverage() -> Callable[..., Coverage]:
    def factory(
        instruction: Optional[Counter] = None,
        branch: Optional[Counter] = None,
        line: Optional[Counter] = None,
        complexity: Optional[Counter] = None,
        method: Optional[Counter] = None,
        clazz: Optional[Counter] = None,
    ) -> Coverage:
        default = Counter(missed=0, covered=10)
        return Coverage(
            instruction=instruction if instruction is not None else Counter(missed=0, covered=10),
            branch=branch if branch is not None else Counter(missed=0, covered=10),
            line=line if line is not None else Counter(missed=0, covered=10),
            complexity=complexity if complexity is not None else Counter(missed=0, covered=10),
            method=method if method is not None else Counter(missed=0, covered=10),
            clazz=clazz if clazz is not None else Counter(missed=0, covered=10),
        )

    return factory


@pytest.fixture
def make_file_coverage() -> Callable[..., FileCoverage]:
    def factory(
        file_name: str = "Example.java",
        file_path: str = "com/example",
        instruction: Optional[Counter] = None,
        branch: Optional[Counter] = None,
        line: Optional[Counter] = None,
        complexity: Optional[Counter] = None,
        method: Optional[Counter] = None,
        clazz: Optional[Counter] = None,
    ) -> FileCoverage:
        return FileCoverage(
            file_name=file_name,
            file_path=file_path,
            instruction=instruction if instruction is not None else Counter(missed=0, covered=10),
            branch=branch if branch is not None else Counter(missed=0, covered=10),
            line=line if line is not None else Counter(missed=0, covered=10),
            complexity=complexity if complexity is not None else Counter(missed=0, covered=10),
            method=method if method is not None else Counter(missed=0, covered=10),
            clazz=clazz if clazz is not None else Counter(missed=0, covered=10),
        )

    return factory


@pytest.fixture
def make_report_file_coverage() -> Callable[..., ReportFileCoverage]:
    def factory(
        path: str = "report.xml",
        name: str = "Test Report",
        overall_coverage: Optional[Coverage] = None,
        changed_files_coverage: Optional[dict[str, FileCoverage]] = None,
        module_name: Optional[str] = None,
    ) -> ReportFileCoverage:
        if overall_coverage is None:
            overall_coverage = Coverage(
                instruction=Counter(missed=0, covered=10),
                branch=Counter(missed=0, covered=10),
                line=Counter(missed=0, covered=10),
                complexity=Counter(missed=0, covered=10),
                method=Counter(missed=0, covered=10),
                clazz=Counter(missed=0, covered=10),
            )
        return ReportFileCoverage(
            path=path,
            name=name,
            overall_coverage=overall_coverage,
            changed_files_coverage=changed_files_coverage if changed_files_coverage is not None else {},
            module_name=module_name,
        )

    return factory


@pytest.fixture
def make_module() -> Callable[..., Module]:
    def factory(
        name: str = "test-module",
        unique_path: str = "test_project/test-module",
        min_coverage_overall: float = 80.0,
        min_coverage_changed_files: float = 70.0,
        min_coverage_changed_per_file: float = 60.0,
    ) -> Module:
        return Module(
            name=name,
            unique_path=unique_path,
            min_coverage_overall=min_coverage_overall,
            min_coverage_changed_files=min_coverage_changed_files,
            min_coverage_changed_per_file=min_coverage_changed_per_file,
        )

    return factory


@pytest.fixture
def make_evaluated_report_coverage() -> Callable[..., EvaluatedReportCoverage]:
    def factory(
        name: str = "test-report",
        module_name: str = "Unknown",
        overall_passed: bool = True,
        overall_coverage_reached: float = 80.0,
        overall_coverage_threshold: float = 70.0,
        avg_changed_files_passed: bool = True,
        avg_changed_files_coverage_reached: float = 75.0,
        changed_files_threshold: float = 70.0,
        per_changed_file_threshold: float = 60.0,
        changed_files_passed: Optional[dict[str, bool]] = None,
        changed_files_coverage_reached: Optional[dict[str, float]] = None,
    ) -> EvaluatedReportCoverage:
        erc = EvaluatedReportCoverage(name=name, module_name=module_name)
        erc.overall_passed = overall_passed
        erc.overall_coverage_reached = overall_coverage_reached
        erc.overall_coverage_threshold = overall_coverage_threshold
        erc.avg_changed_files_passed = avg_changed_files_passed
        erc.avg_changed_files_coverage_reached = avg_changed_files_coverage_reached
        erc.changed_files_threshold = changed_files_threshold
        erc.per_changed_file_threshold = per_changed_file_threshold
        erc.changed_files_passed = changed_files_passed if changed_files_passed is not None else {}
        erc.changed_files_coverage_reached = (
            changed_files_coverage_reached if changed_files_coverage_reached is not None else {}
        )
        return erc

    return factory
