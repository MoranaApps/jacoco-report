"""
Constants used in the action
"""

# Action inputs environment variables
TOKEN = "token"

PATHS = "paths"
DEFAULT_PATHS = "**/jacoco.xml"
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
GLOBAL_OVERALL_SCOPE_ALL = "all"
GLOBAL_OVERALL_SCOPE_GROUPS_ONLY = "groups-only"
DEFAULT_GLOBAL_OVERALL_SCOPE = GLOBAL_OVERALL_SCOPE_ALL
UPDATE_COMMENT = "update-comment"
PASS_SYMBOL = "pass-symbol"
FAIL_SYMBOL = "fail-symbol"
FAIL_ON_THRESHOLD = "fail-on-threshold"
DEBUG = "debug"

BASELINE_PATHS = "baseline-paths"

CA_BUNDLE = "ca-bundle"

# fail-on-threshold values
OVERALL = "overall"
CHANGED_FILES_AVERAGE = "changed-files-average"
CHANGED_FILE = "changed-file"

# GitHub-injected metadata environment variables (no INPUT_ prefix)
GITHUB_RUN_ID = "GITHUB_RUN_ID"
# GITHUB_ACTION_REF is empty in composite action steps (actions/runner#2473), so the ref is parsed from this path
GITHUB_ACTION_PATH = "GITHUB_ACTION_PATH"
# GitHub Enterprise Server: the runner sets these to the instance's own URLs (github.com when unset)
GITHUB_API_URL = "GITHUB_API_URL"
GITHUB_SERVER_URL = "GITHUB_SERVER_URL"
DEFAULT_GITHUB_API_URL = "https://api.github.com"
DEFAULT_GITHUB_SERVER_URL = "https://github.com"

# PR comment footer: where the action lives
ACTION_REPOSITORY = "MoranaApps/jacoco-report"
ACTION_REPOSITORY_URL = f"https://github.com/{ACTION_REPOSITORY}"
