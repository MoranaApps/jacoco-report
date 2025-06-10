"""
The main module to run the JaCoCo GitHub Action adding the Json report to the pull request.
"""

import logging
import sys

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.utils.enums import FailOnThresholdEnum
from jacoco_report.utils.gh_action import set_action_output, set_action_failed, set_action_output_text
from jacoco_report.utils.logging_config import setup_logging


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
    set_action_output_text("reports-coverage", jr.evaluated_coverage_reports)
    set_action_output_text("modules-coverage", jr.evaluated_coverage_modules)

    logger.debug("Action output 'coverage-overall' set to: %s", jr.total_overall_coverage)
    logger.debug("Action output 'coverage-changed-files' set to: %s", jr.total_changed_files_coverage)
    logger.debug("Action output 'coverage-overall-passed' set to: %s", jr.total_overall_coverage_passed)
    logger.debug("Action output 'coverage-changed-files-passed' set to: %s", jr.total_changed_files_coverage_passed)
    logger.debug("Action output 'reports-coverage' set to: %s", jr.evaluated_coverage_reports)
    logger.debug("Action output 'modules-coverage' set to: %s", jr.evaluated_coverage_modules)
    logger.debug("Action output 'violations' set to: %s", jr.violations)

    if len(jr.violations) > 0:
        logger.error("JaCoCo Report GitHub Action - failed.")

        thresholds = ActionInputs.get_fail_on_threshold()

        # Map enum values to the corresponding evaluation flags
        threshold_checks = {
            FailOnThresholdEnum.OVERALL: jr.reached_threshold_overall,
            FailOnThresholdEnum.CHANGED_FILES_AVERAGE: jr.reached_threshold_changed_files_average,
            FailOnThresholdEnum.PER_CHANGED_FILE: jr.reached_threshold_per_change_file,
        }

        # Fail if any configured threshold was not reached
        fail = any(not passed for threshold, passed in threshold_checks.items() if threshold in thresholds)
        set_action_failed(messages=jr.violations, fail=fail)
    else:
        logger.info("JaCoCo Report GitHub Action - success.")
        sys.exit(0)


if __name__ == "__main__":
    run()
