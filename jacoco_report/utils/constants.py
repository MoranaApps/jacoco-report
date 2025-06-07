"""
Constants used in the action
"""

# Action inputs environment variables
TOKEN = "token"

PATHS = "paths"
EXCLUDE_PATHS = "exclude-paths"

GLOBAL_THRESHOLDS = "global-thresholds"

TITLE = "title"
PR_NUMBER = "pr-number"
METRIC = "metric"

SENSITIVITY = "sensitivity"
COMMENT_MODE = "comment-mode"
MODULES = "modules"
MODULES_THRESHOLDS = "modules-thresholds"

SKIP_UNCHANGED = "skip-unchanged"
UPDATE_COMMENT = "update-comment"
PASS_SYMBOL = "pass-symbol"
FAIL_SYMBOL = "fail-symbol"
FAIL_ON_THRESHOLD = "fail-on-threshold"
DEBUG = "debug"

BASELINE_PATHS = "baseline-paths"

# fail-on-threshold values
OVERALL = "overall"
CHANGED_FILES_AVERAGE = "changed-files-average"
PER_CHANGED_FILES = "per-changed-file"
