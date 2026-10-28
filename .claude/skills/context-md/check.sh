#!/usr/bin/env bash
# From agentic-defaults. Kit updates replace this file: don't edit it. Project rules go in AGENTS.md "This project".
# Lists CONTEXT.md files that may need an update: code under them changed, but they didn't.
# A nudge, not a verdict: internal refactors and bug fixes that restore documented behavior need no update.
# Read-only. Works with bash 3.2 (macOS) and Git Bash (Windows).
#
# Usage: bash check.sh [--base <ref>] [--strict | --hook]
#   default       uncommitted changes (staged, unstaged, untracked) against HEAD
#   --base <ref>  also include commits since <ref>, e.g. --base origin/main for a branch or pull request
#   --strict      exit 1 when there is something to check (for CI or pre-commit)
#   --hook        for an agent's end-of-turn hook (Claude Code "Stop", GitHub Copilot "agentStop"): prints
#                 {"decision": "block", "reason": ...} on stdout, once per distinct finding, which both tools
#                 read as "keep working with this instruction". Always exits 0. Prints nothing when there is
#                 nothing new, or when stdin says the agent is already continuing because of this hook
#                 ("stop_hook_active": true).

set -u
base=""
strict=0
hook=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base) base="${2:-}"; shift 2 ;;
    --strict) strict=1; shift ;;
    --hook) hook=1; shift ;;
    -h|--help) sed -n '3,16p' "$0"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ "$hook" = 1 ]; then
  # Never block a continuation the hook itself caused, and never break a session outside git.
  input=$(cat 2>/dev/null || true)
  printf '%s' "$input" | grep -Eq '"stop_hook_active"[[:space:]]*:[[:space:]]*true' && exit 0
  git rev-parse --show-toplevel >/dev/null 2>&1 || exit 0
fi

root=$(git rev-parse --show-toplevel 2>/dev/null) || { echo "Not a git repository." >&2; exit 2; }
cd "$root" || exit 2

changed=$(mktemp); owners=$(mktemp); kit=$(mktemp)
trap 'rm -f "$changed" "$owners" "$kit"' EXIT

# -z gives raw paths; without it git puts quotes around paths that contain quotes or backslashes.
{
  if git rev-parse --verify -q HEAD >/dev/null; then
    git diff --name-only -z HEAD
  else
    git ls-files -z
  fi
  git ls-files -z --others --exclude-standard
  if [ -n "$base" ]; then
    git diff --name-only -z "$base"...HEAD || exit 2
  fi
} | tr '\0' '\n' | sort -u > "$changed"

# Files installed by agd belong to their source, not to the project: skip every path .agd.lock lists
# ("file <source> <path> <blob>"), in the working tree, at HEAD and, with --base, where the branch started,
# so files that an update or "agd remove" deleted are skipped too.
{
  [ -f .agd.lock ] && cat .agd.lock
  git show HEAD:.agd.lock 2>/dev/null
  if [ -n "$base" ]; then
    start=$(git merge-base "$base" HEAD 2>/dev/null) && git show "$start:.agd.lock" 2>/dev/null
  fi
} | awk '$1 == "file" && NF >= 4 { path = $3; for (i = 4; i < NF; i++) path = path " " $i; print path }' | sort -u > "$kit"

# Changes that never require a CONTEXT.md update: docs, private notes, housekeeping files, tests, lock files.
skip='(^|/)CONTEXT\.md$|^\.agd\.lock$|\.md$|^docs?/|^\.local_context/|(^|/)(LICENSE|COPYING|NOTICE|CHANGELOG|VERSION)[^/]*$|(^|/)\.(gitignore|gitattributes|editorconfig|mailmap)$|(^|/)(test|tests|__tests__|spec|specs|e2e)/|(^|/)test_[^/]+\.py$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$|Tests?\.(java|kt|cs|swift|scala)$|(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|uv\.lock|Cargo\.lock|go\.sum|Gemfile\.lock|composer\.lock)$'

# Dependency bumps (Renovate, Dependabot) change only versions, which no CONTEXT.md records. A manifest is
# skipped when its removed and added lines match once versions and digests are masked; a new or removed
# dependency, any other edit, or a new manifest still counts.
manifest='(^|/)(requirements[^/]*\.txt|constraints[^/]*\.txt|pyproject\.toml|Pipfile|package\.json|go\.mod|Cargo\.toml|Gemfile|pom\.xml|build\.gradle(\.kts)?|libs\.versions\.toml|Dockerfile[^/]*|\.tool-versions|\.python-version|\.nvmrc|versions\.tf)$|^\.github/workflows/[^/]+\.ya?ml$'
since=HEAD
[ -n "$base" ] && since=$(git merge-base "$base" HEAD 2>/dev/null)
version_only() {
  [ -n "$since" ] && [ -f "$1" ] && git cat-file -e "$since:$1" 2>/dev/null || return 1
  lines=$(git diff -U0 "$since" -- "$1" | grep -Ev '^(---|\+\+\+) ' | grep -E '^[-+]' |
    sed -E 's/[0-9a-f]{7,}/H/g; s/v?[0-9]+([.][0-9A-Za-z]+)*([-+][0-9A-Za-z.]+)?/V/g')
  [ "$(printf '%s\n' "$lines" | sed -n 's/^-//p' | sort)" = "$(printf '%s\n' "$lines" | sed -n 's/^+//p' | sort)" ]
}

# Pair each changed code file with the nearest CONTEXT.md above it.
grep -Ev "$skip" "$changed" | awk -v kit="$kit" '
  BEGIN { while ((getline line < kit) > 0) installed[line] = 1 }
  !($0 in installed)
' | while IFS= read -r file; do
  [ -n "$file" ] || continue
  printf '%s\n' "$file" | grep -Eq "$manifest" && version_only "$file" && continue
  dir=$(dirname "$file")
  owner="-"
  while :; do
    if [ "$dir" = "." ]; then
      [ -f CONTEXT.md ] && owner="CONTEXT.md"
      break
    fi
    if [ -f "$dir/CONTEXT.md" ]; then owner="$dir/CONTEXT.md"; break; fi
    dir=$(dirname "$dir")
  done
  printf '%s\t%s\n' "$owner" "$file"
done > "$owners"

# Keep owners whose CONTEXT.md was not itself changed, grouped, with up to three example files each.
report=$(awk -F'\t' -v changed="$changed" '
  BEGIN { while ((getline line < changed) > 0) touched[line] = 1 }
  $1 != "-" && !($1 in touched) {
    n[$1]++
    if (n[$1] <= 3) ex[$1] = ex[$1] (n[$1] > 1 ? ", " : "") $2
  }
  END { for (o in n) printf "- %s: %s%s\n", o, ex[o], (n[o] > 3 ? " (+" n[o] - 3 " more)" : "") }
' "$owners" | sort)
uncovered=$(awk -F'\t' '$1 == "-" { print $2 }' "$owners" | head -5)

if [ "$hook" = 1 ]; then
  [ -n "$report" ] || exit 0
  # Raise each distinct finding once, so the agent isn't nagged at the end of every turn.
  seen="$(git rev-parse --git-dir)/agentic-defaults-context-check"
  fingerprint=$(printf '%s\n' "$report" | cksum)
  [ -f "$seen" ] && [ "$(cat "$seen")" = "$fingerprint" ] && exit 0
  printf '%s\n' "$fingerprint" > "$seen"
  # JSON-escape the message (backslashes, quotes, tabs, newlines) without needing jq.
  reason=$({
    echo "Context check before you finish: code changed under these CONTEXT.md files, but they didn't."
    printf '%s\n' "$report"
    echo "Update each one your change made wrong or incomplete, or say in one line why none needs it."
  } | awk '{ gsub(/\\/, "\\\\"); gsub(/"/, "\\\""); gsub(/\t/, "\\t"); printf "%s%s", (NR > 1 ? "\\n" : ""), $0 }')
  printf '{"decision": "block", "reason": "%s"}\n' "$reason"
  exit 0
fi

if [ -n "$report" ]; then
  echo "CONTEXT.md files to check (code under them changed, they did not):"
  echo
  printf '%s\n' "$report"
  echo
  echo "Update each one the change made wrong or incomplete (see the context-md skill)."
  echo "No update is needed for internal refactors or bug fixes that restore documented behavior."
fi
if [ -n "$uncovered" ]; then
  [ -n "$report" ] && echo
  echo "No CONTEXT.md covers these changed files (consider a project scan):"
  printf '%s\n' "$uncovered" | sed 's/^/- /'
fi
if [ -z "$report" ] && [ -z "$uncovered" ]; then
  echo "Nothing to check: no code changed, or every CONTEXT.md covering it was updated."
fi

[ "$strict" = 1 ] && [ -n "$report" ] && exit 1
exit 0
