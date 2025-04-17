"""
The main module to run the JaCoCo GitHub Action adding the Jajson report to the pull request.
"""

import logging
import sys

from jacoco_report.action_inputs import ActionInputs
from jacoco_report.jacoco_report import JaCoCoReport
from jacoco_report.utils.gh_action import set_action_output, set_action_failed, set_action_output_text
from jacoco_report.utils.logging_config import setup_logging

# TODO & notes
'''
Config:
    sensitivity: "detail"
    comment-mode: 'module'
    skip-not-changed: 'true'
    modules: ${{ env.MODULES }}
    modules-thresholds: ${{ env.MODULES_THRESHOLDS }}

all modules defined
    TODO - co kdyz existuje jacoxo.xml mimo definovane moduly ???
        - nejaky orphan module
        
    
several module-thresholds commented out
    - TODO - ty commented se dostavaji do kodu jako input - jaky to ma dopad
    - TODO - dodat detekci na # a ty vyradit uz na  vstupu?

Outputs
- TODO - to co je v komentu uz pak neni uvedeno jako error - cast violations?
    - tady bude potrebna revize, zda toto plati nebo ne
    - kazda chyba by zde mela byt videt, aby se vystup dal pouzit jako ekvivalent ke komentum


Bugs:
- TODO - proc se v module regimu negenerujic komenty pro vsechny moduly?

Log
Generating PR comment(s).
Generating 0 pr comments...     - znamena tahle hlaska, ze se negeneruje new comment? - DUSLEDEK Bugu, rekl bych
  rerun - uz je jich tam 7 - ale to je stale malo proc?

pozorovani
- vioaltions by nemely obsahovat report errors v pripade module regime - tam doslo k merge a resi se cely module
- nabizi se myslenka pridat reports table s prehledem overall

TESTED
- modules detection for report files - OK
- module loading - OK + TODO - modules se spatne prevadeji do stringu: class Module - check str, repr method


Visible comments
- aws - failing 0/43 %
- awsutils - failing 0/43 %
- bootstrap - failing 22,4/43 %
- config - failing 0/43 %
- datamodel - 33,74/43 %
- restcontroller - 32,63/43 %
- user-identity-info - 42,09/43 %

Not visible comments
- domain-questions-spring-web - 0/43 %
- domnain-execution-api - 30,99/43 %
- use-identity-info-spring0controller - 11,9/43 %
- data-cataloging-spring-web - 41,03/43 %
- data-access-spring-web - 0/43 %
- user-identity-info-implementation - 39,19/43 %
- notification-delivery-api - 0/43 %
- data-measurement-impementation - 0/43 %
- feed-management-api - 0/43 %
- domain-management-api - 28,21/43 %

'''


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
        set_action_failed(messages=jr.violations, fail=ActionInputs.get_fail_on_threshold())
    else:
        logger.info("JaCoCo Report GitHub Action - success.")
        sys.exit(0)


if __name__ == "__main__":
    run()
