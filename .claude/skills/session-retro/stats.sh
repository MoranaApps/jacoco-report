#!/usr/bin/env bash
# From agentic-defaults. Kit updates replace this file: don't edit it. Project rules go in AGENTS.md "This project".
# Read-only numbers on a Claude Code session for a session retro: time, models, tokens, prompts, tool calls,
# subagents, git changes, and the project's usual numbers from earlier retros. Prints counts only, never
# text from the session. With --prompts, it prints the user's prompts instead, for the agent to label
# locally; that text must not go into notes or issues.
# Reads Claude Code's local session files, an undocumented format that can change.
# Needs git and POSIX tools; the session numbers need jq. Works with bash 3.2 (macOS) and Git Bash (Windows).
# Usage: bash stats.sh [--prompts] [session.jsonl]
#   Without a file: the session in CLAUDE_CODE_SESSION_ID, else the newest session for this folder.

set -u
projects=${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects
log=.local_context/feedback/log.tsv
has() { command -v "$1" >/dev/null 2>&1; }

prompts=0
if [ "${1:-}" = "--prompts" ]; then prompts=1; shift; fi

session="" how=""
if [ $# -gt 0 ]; then
  session=$1 how="given"
elif [ -n "${CLAUDE_CODE_SESSION_ID:-}" ]; then
  for f in "$projects"/*/"$CLAUDE_CODE_SESSION_ID".jsonl; do
    if [ -f "$f" ]; then session=$f how="CLAUDE_CODE_SESSION_ID"; break; fi
  done
fi
if [ -z "$session" ] && [ $# -eq 0 ]; then
  # Claude Code names a project's folder after its path, with every other character than a letter or digit as "-".
  # pwd -W gives Git Bash's Windows path (C:/...), which Claude Code uses on Windows.
  for dir in "$(pwd)" "$(pwd -P)" "$(pwd -W 2>/dev/null)"; do
    [ -n "$dir" ] || continue
    newest=$(ls -t "$projects/$(printf '%s' "$dir" | sed 's/[^A-Za-z0-9]/-/g')"/*.jsonl 2>/dev/null | head -1)
    if [ -n "$newest" ]; then session=$newest how="newest for this folder; parallel sessions can mix this up"; break; fi
  done
fi
[ -n "$session" ] && [ ! -f "$session" ] && session=""

# Shared by both modes: what counts as a prompt the user typed.
prelude='
  def content: .message.content;
  def texts: if (content | type) == "string" then [content] else [content[]? | select(.type == "text") | .text] end;
  def results: if (content | type) == "array" then [content[] | select(.type == "tool_result")] else [] end;
  def typed: texts | map(select(test("^(<(local-command|command-|task-notification|system-reminder|ide_)|\\[Request interrupted)") | not));
  def entries: [inputs | input_filename as $f | (try fromjson catch null) | select(type == "object") | .file = $f];
  def user_turns: map(select(.type == "user" and (.isMeta | not) and (.isCompactSummary | not) and (.isSidechain | not)
    and (results | length) == 0));
'

if [ "$prompts" = 1 ]; then
  [ -n "$session" ] || { echo "No Claude Code session found for this folder. Pass a session file: bash stats.sh --prompts <session.jsonl>" >&2; exit 1; }
  has jq || { echo "Listing prompts needs jq (https://jqlang.org)" >&2; exit 1; }
  jq -nrR "$prelude"'
    entries | user_turns | map(typed | join(" ") | gsub("\\s+"; " ") | ltrimstr(" ") | select(length > 0))
    | to_entries[] | "\(.key + 1). \(if (.value | length) > 300 then .value[:300] + "…" else .value end)"
  ' "$session"
  exit
fi

start=""
echo "Session numbers (Claude Code's local files, counts only):"
if [ -z "$session" ]; then
  echo "- No Claude Code session found for this folder. Pass a session file: bash stats.sh <session.jsonl>"
else
  echo "- Session: $(basename "$session" .jsonl) ($how)"
  if ! has jq; then
    echo "- Numbers: not shown: install jq to read them (https://jqlang.org)"
  else
    out=$(mktemp)
    trap 'rm -f "$out"' EXIT
    # Subagents of a session keep their own files in <session>/subagents/.
    set -- "$session"
    for f in "${session%.jsonl}"/subagents/*.jsonl; do [ -f "$f" ] && set -- "$@" "$f"; done
    jq -nrR --arg main "$session" "$prelude"'
      def counts: group_by(.) | map({k: .[0], n: length}) | sort_by(-.n);
      entries as $all
      | ($all | map(select(.file == $main))) as $m
      | ($all | map(select(.type == "assistant" and (.message | type) == "object"))) as $a
      # Claude Code logs one entry per content block, so an API call can appear several times with one id.
      | ($a | map(select(.message.model != "<synthetic>")) | group_by(.message.id // .uuid) | map(.[-1])) as $calls
      | ($m | user_turns) as $u
      | ($m | map(.timestamp // empty | sub("\\.[0-9]+"; "") | try fromdateiso8601 catch empty)) as $times
      | ([$a[] | content[]? | select(.type == "tool_use") | .name]) as $tools
      | def sum(f): map(.message.usage | f // 0) | add // 0;
      (if ($times | length) > 0 then
        "- Time: \((($times | max) - ($times | min)) / 60 | round) min from first to last entry, idle time included",
        "start=\($times | min)"
      else empty end),
      "- Models: \($calls | map(.message.model) | counts | map("\(.k) (\(.n) calls)") | join(", "))",
      "- Tokens: input \($calls | sum(.input_tokens)), output \($calls | sum(.output_tokens)), cache read \($calls | sum(.cache_read_input_tokens)), cache write \($calls | sum(.cache_creation_input_tokens))",
      "- Prompts: \($u | map(select(typed | length > 0)) | length), interrupts: \($u | map(select(texts | any(startswith("[Request interrupted")))) | length), denied tool calls: \($m | map(select(.type == "user" and .permissionDecision.decision? == "reject")) | length)",
      "- Tool calls: \($tools | length), failed: \([$all[] | select(.type == "user") | results[] | select(.is_error == true)] | length)\(if ($tools | length) > 0 then " (\($tools | counts | .[:5] | map("\(.k) \(.n)") | join(", ")))" else "" end)",
      "- Subagents: \($all | map(.file) | unique | map(select(. != $main)) | length)"
    ' "$@" >"$out" 2>/dev/null || echo "- Numbers: not shown: jq couldn't read the session file"
    start=$(sed -n 's/^start=//p' "$out")
    sed '/^start=/d' "$out"
  fi
fi

# lines: "+added -removed" summed over git --numstat output on stdin.
lines() { awk '{ if ($1 != "-") a += $1; if ($2 != "-") r += $2 } END { printf "+%d -%d", a, r }'; }

if root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$root" || exit 1
  echo
  echo "Git:"
  if [ -n "$start" ]; then
    echo "- Commits since the session started: $(git rev-list --count --since="@$start" HEAD 2>/dev/null || echo 0)" \
      "($(git log --since="@$start" --numstat --format= 2>/dev/null | lines))"
  fi
  base=HEAD
  git rev-parse -q --verify HEAD >/dev/null || base=$(git hash-object -t tree /dev/null)
  echo "- Uncommitted: $(git diff --numstat "$base" | wc -l | tr -d ' ') changed files" \
    "($(git diff --numstat "$base" | lines)), $(git ls-files --others --exclude-standard | wc -l | tr -d ' ') new files"
fi

# The project's usual numbers: medians over the last 10 retros in the log, found by column name.
echo
echo "Earlier retros:"
rows=0
[ -f "$log" ] && rows=$(awk 'NR > 1 && NF' "$log" | wc -l | tr -d ' ')
if [ "$rows" -lt 3 ]; then
  echo "- Usual for this project: no baseline yet (fewer than 3 retros in $log)"
else
  median() { # <column name>
    awk -F '\t' -v col="$1" 'NR == 1 { for (i = 1; i <= NF; i++) if ($i == col) c = i; next } NF && c { print $c }' "$log" \
      | tail -10 | sort -n | awk '{ v[NR] = $1 } END { print v[int((NR + 1) / 2)] }'
  }
  used=$rows
  [ "$used" -gt 10 ] && used=10
  echo "- Usual for this project (median of the last $used retros): output tokens $(median output_tokens), tool calls $(median tool_calls)"
fi
