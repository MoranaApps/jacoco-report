"""
The main module to run the JaCoCo GitHub Action adding the Json report to the pull request.
"""

import logging
import sys
from typing import Optional

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.utils.enums import FailOnThresholdEnum
from jacoco_report.utils.gh_action import set_action_output, set_action_failed, set_action_output_text
from jacoco_report.utils.logging_config import setup_logging


def _delta_output(delta: Optional[float]) -> str:
    """Return a Δ output value: empty when there is no baseline to compare with."""
    return "" if delta is None else str(delta)


def _verified_output(verified: Optional[bool]) -> str:
    """Return the baseline-verified output: empty when baseline-sha is not set, else 'true' or 'false'."""
    return "" if verified is None else str(verified).lower()


def run() -> None:
    """
    The main function to run the JaCoCo GitHub Action adding the JaCoCo coverage report to the pull request.

    @return: None
    """
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting JaCoCo Report GitHub Action validation of inputs.")

    # Validate the action inputs
    ActionInputs().validate_inputs()

    logger.info("Starting JaCoCo Report GitHub Action.")

    # Generate the Living documentation
    jr = JaCoCoReport()
    jr.run()

    # Set the output for the GitHub Action
    set_action_output("coverage-overall", str(jr.total_overall_coverage))
    set_action_output("coverage-changed-files", str(jr.total_changed_files_coverage))
    set_action_output("coverage-overall-passed", str(jr.total_overall_coverage_passed))
    set_action_output("coverage-changed-files-passed", str(jr.total_changed_files_coverage_passed))
    set_action_output("coverage-overall-delta", _delta_output(jr.total_overall_coverage_delta))
    set_action_output("coverage-changed-files-delta", _delta_output(jr.total_changed_files_coverage_delta))
    set_action_output("baseline-verified", _verified_output(jr.baseline_verified))
    set_action_output_text("reports-coverage", jr.evaluated_coverage_reports)
    set_action_output_text("groups-coverage", jr.evaluated_coverage_groups)

    logger.debug("Action output 'coverage-overall' set to: %s", jr.total_overall_coverage)
    logger.debug("Action output 'coverage-changed-files' set to: %s", jr.total_changed_files_coverage)
    logger.debug("Action output 'coverage-overall-passed' set to: %s", jr.total_overall_coverage_passed)
    logger.debug("Action output 'coverage-changed-files-passed' set to: %s", jr.total_changed_files_coverage_passed)
    logger.debug("Action output 'coverage-overall-delta' set to: %s", jr.total_overall_coverage_delta)
    logger.debug("Action output 'coverage-changed-files-delta' set to: %s", jr.total_changed_files_coverage_delta)
    logger.debug("Action output 'baseline-verified' set to: %s", _verified_output(jr.baseline_verified))
    logger.debug("Action output 'reports-coverage' set to: %s", jr.evaluated_coverage_reports)
    logger.debug("Action output 'groups-coverage' set to: %s", jr.evaluated_coverage_groups)

    if len(jr.violations) > 0:
        thresholds = ActionInputs.get_fail_on_threshold()

        # Map enum values to the corresponding evaluation flags
        threshold_checks = {
            FailOnThresholdEnum.OVERALL: jr.reached_threshold_overall,
            FailOnThresholdEnum.CHANGED_FILES_AVERAGE: jr.reached_threshold_changed_files_average,
            FailOnThresholdEnum.PER_CHANGED_FILE: jr.reached_threshold_per_change_file,
            FailOnThresholdEnum.FAIL_UNCHANGED: jr.reached_threshold_fail_unchanged,
            FailOnThresholdEnum.NO_DECREASE: jr.reached_threshold_no_decrease,
        }

        # Fail if any configured threshold was not reached
        threshold_failure = any(not passed for threshold, passed in threshold_checks.items() if threshold in thresholds)
        fail = jr.has_operational_failure or threshold_failure

        if fail:
            logger.error("JaCoCo Report GitHub Action - failed.")
        else:
            logger.info("JaCoCo Report GitHub Action - violations detected but fail-on-threshold is disabled.")
        set_action_failed(messages=jr.violations, fail=fail)
    else:
        logger.info("JaCoCo Report GitHub Action - success.")
        sys.exit(0)


if __name__ == "__main__":
    run()
