"""
Constants used in the action
"""

# Action inputs environment variables
TOKEN = "token"

PATHS = "paths"
DEFAULT_PATHS = "**/jacoco.xml"  # must match the `default:` value for `paths` in action.yml
EXCLUDE_PATHS = "exclude-paths"

GLOBAL_THRESHOLDS = "global-thresholds"
DEFAULT_GLOBAL_THRESHOLDS = "0.0*0.0"

REPORT_THRESHOLDS_DEFAULT = "report-thresholds-default"
DEFAULT_REPORT_THRESHOLDS_DEFAULT = "0.0*0.0*0.0"

TITLE = "title"
PR_NUMBER = "pr-number"
METRIC = "metric"

COMMENT_LEVEL = "comment-level"
REPORT_GROUPS = "report-groups"

SKIP_UNCHANGED = "skip-unchanged"
EVALUATE_UNCHANGED = "evaluate-unchanged"
GLOBAL_OVERALL_SCOPE = "global-overall-scope"
DEFAULT_GLOBAL_OVERALL_SCOPE = "all"
GLOBAL_OVERALL_SCOPE_ALL = "all"
GLOBAL_OVERALL_SCOPE_GROUPS_ONLY = "groups-only"
UPDATE_COMMENT = "update-comment"
PASS_SYMBOL = "pass-symbol"
FAIL_SYMBOL = "fail-symbol"
FAIL_ON_THRESHOLD = "fail-on-threshold"
DEBUG = "debug"

BASELINE_PATHS = "baseline-paths"

# fail-on-threshold values
OVERALL = "overall"
CHANGED_FILES_AVERAGE = "changed-files-average"
CHANGED_FILE = "changed-file"

# GitHub-injected metadata environment variables (no INPUT_ prefix)
GITHUB_RUN_ID = "GITHUB_RUN_ID"
GITHUB_RUN_STARTED_AT = "GITHUB_RUN_STARTED_AT"
GITHUB_ACTION_REF = "GITHUB_ACTION_REF"
