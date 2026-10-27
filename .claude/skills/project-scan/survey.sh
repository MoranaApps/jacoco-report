#!/usr/bin/env bash
# From agentic-defaults. Kit updates replace this file: don't edit it. Project rules go in AGENTS.md "This project".
# Read-only survey of a project for AI discovery. Prints a compact Markdown overview.
# Needs only git and POSIX tools; uses scc or tokei for language stats when installed.
# Works with bash 3.2 (macOS) and Git Bash (Windows).
# Usage: bash survey.sh [project-dir]

set -u
cd "${1:-.}" || exit 1

list=$(mktemp)
trap 'rm -f "$list"' EXIT

if root=$(git rev-parse --show-toplevel 2>/dev/null); then
  cd "$root" || exit 1
  is_git=1
  # Tracked plus untracked-but-not-ignored files.
  git ls-files --cached --others --exclude-standard > "$list"
else
  is_git=0
  find . \( -name .git -o -name node_modules -o -name .venv -o -name venv -o -name target \
    -o -name build -o -name dist -o -name .local_context -o -name __pycache__ -o -name '.*_cache' \
    -o -name .gradle -o -name .idea -o -name .next -o -name coverage \) -prune \
    -o -type f ! -name '*.pyc' ! -name .DS_Store -print \
    | sed 's|^\./||' > "$list"
fi

has() { command -v "$1" >/dev/null 2>&1; }
section() { printf '\n## %s\n\n' "$1"; }
bullets() { sed 's/^/- /'; }
# Collapse "  12 path" lines from uniq -c into "- path (12)".
counted() { sed -E 's/^ *([0-9]+) (.*)$/- \2 (\1)/'; }

echo "# Survey: $(basename "$(pwd)")"
echo
echo "- Files: $(wc -l < "$list" | tr -d ' ')"
if [ "$is_git" = 1 ]; then
  echo "- Branch: $(git branch --show-current 2>/dev/null)"
  echo "- Commits: $(git rev-list --count HEAD 2>/dev/null || echo 0)"
  echo "- Last commit: $(git log -1 --format=%cd --date=short 2>/dev/null)"
  # A count only, never names or emails: a hint for the project profile's Team dimension.
  echo "- Contributors, last 12 months: $(git log --since='12 months ago' --format='%ae' 2>/dev/null | sort -u | grep -c .)"
else
  echo "- Not a git repository"
fi

section "Languages"
if has scc; then
  scc --no-cocomo --no-complexity --no-size --sort code 2>/dev/null | grep -v -e '───' -e '^Total' | head -16
elif has tokei; then
  tokei --sort code 2>/dev/null | grep -v -e '===' -e '---' | head -16
else
  echo "Files by extension (install scc or tokei for line counts):"
  echo
  awk -F/ '{ n = $NF; i = index(n, "."); if (i > 1) { sub(/^[^.]*\./, "", n); sub(/^.*\./, "", n); print tolower(n) } }' "$list" \
    | sort | uniq -c | sort -rn | head -12 | counted
fi

section "Structure (files per directory)"
awk -F/ 'NF > 1 { print $1 "/" }' "$list" | sort | uniq -c | sort -rn | head -25 | counted
echo
echo "Largest subdirectories:"
echo
awk -F/ 'NF > 2 { print $1 "/" $2 "/" }' "$list" | sort | uniq -c | sort -rn | head -15 | counted
echo
echo "Root files: $(awk -F/ 'NF == 1' "$list" | head -40 | tr '\n' ' ')"

section "Build, dependency, runtime and CI files"
grep -E '(^|/)(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|pnpm-workspace\.yaml|bun\.lockb?|nx\.json|turbo\.json|lerna\.json|deno\.jsonc?|tsconfig\.json|pyproject\.toml|setup\.py|setup\.cfg|requirements[^/]*\.txt|Pipfile|Pipfile\.lock|poetry\.lock|uv\.lock|tox\.ini|go\.mod|Cargo\.toml|pom\.xml|build\.gradle(\.kts)?|settings\.gradle(\.kts)?|build\.sbt|[^/]+\.csproj|[^/]+\.sln|Gemfile|composer\.json|mix\.exs|build\.zig|CMakeLists\.txt|Makefile|justfile|Taskfile\.ya?ml|Dockerfile[^/]*|(docker-)?compose[^/]*\.ya?ml|Chart\.yaml|main\.tf|root\.hcl|terragrunt\.hcl|\.terraform\.lock\.hcl|\.tflint\.hcl|\.pre-commit-config\.yaml|Procfile|Jenkinsfile|\.gitlab-ci\.yml|azure-pipelines[^/]*\.ya?ml|\.github/workflows/[^/]+\.ya?ml|\.env\.example|\.tool-versions|mise\.toml|\.nvmrc|\.python-version)$' "$list" \
  | awk -F/ 'NF <= 4' | head -40 | bullets

section "Scripts and tasks"
[ -f package.json ] || [ -f Makefile ] || [ -f makefile ] || [ -f GNUmakefile ] || [ -f justfile ] \
  || ls .github/workflows/*.y*ml >/dev/null 2>&1 \
  || echo "None found at the root. Check the build files and README for commands."
if [ -f package.json ]; then
  if has jq; then
    jq -r '.scripts // {} | to_entries[] | "- npm run \(.key): \(.value)"' package.json 2>/dev/null | head -20
  else
    sed -n '/"scripts"/,/}/p' package.json | head -22
  fi
fi
# Stop at the first match: on case-insensitive file systems Makefile and makefile are the same file.
standard="setup run build test lint format check"
makefile=""
for f in GNUmakefile Makefile makefile; do
  if [ -f "$f" ]; then
    makefile="$f"
    grep -E '^[A-Za-z0-9_.-]+:([^=]|$)' "$f" | cut -d: -f1 | grep -v '^[._]' | sort -u | head -20 | sed 's/^/- make /'
    break
  fi
done
if [ -n "$makefile" ]; then
  missing=""
  for target in $standard; do
    grep -Eq "^$target:([^=]|$)" "$makefile" || missing="$missing $target"
  done
  echo
  if [ -n "$missing" ]; then echo "Missing standard make targets:$missing"; else echo "All standard make targets present."; fi
else
  echo "No Makefile, so none of the standard make targets ($standard) exist yet."
fi
[ -f justfile ] && grep -E '^[A-Za-z0-9_-]+[^:=]*:([^=]|$)' justfile | cut -d' ' -f1 | cut -d: -f1 | head -20 | sed 's/^/- just /'
if ls .github/workflows/*.y*ml >/dev/null 2>&1; then
  echo
  echo "Commands run in CI (.github/workflows):"
  echo
  grep -hE '^[[:space:]]*(-[[:space:]]+)?run:[[:space:]]*[^|>[:space:]]' .github/workflows/*.y*ml \
    | sed -E 's/^[[:space:]]*(-[[:space:]]+)?run:[[:space:]]*//' | sort -u | head -15 | bullets
fi

section "Contracts"
contracts=$(grep -Ei '(^|/)(openapi|swagger|asyncapi)[^/]*\.(ya?ml|json)$|\.proto$|\.graphqls?$|\.avsc$|\.schema\.json$' "$list" | head -20)
if [ -n "$contracts" ]; then printf '%s\n' "$contracts" | bullets; else echo "None found by name (API specs, protobuf, GraphQL or JSON schemas)."; fi

section "Tests"
tests=$(grep -E '(^|/)(test|tests|__tests__|spec|specs|e2e|it)/|(^|/)test_[^/]+\.py$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$|Tests?\.(java|kt|cs|swift|scala)$|Spec\.(scala|kt|groovy)$' "$list")
if [ -n "$tests" ]; then
  echo "$(printf '%s\n' "$tests" | wc -l | tr -d ' ') test files. Main locations:"
  echo
  printf '%s\n' "$tests" | sed -n 's|/[^/]*$||p' | cut -d/ -f1-3 | sort | uniq -c | sort -rn | head -8 | counted
else
  echo "No test files found by name. Check the build files for a test setup."
fi

section "Docs and AI context"
grep -E '(^|/)(README[^/]*|CONTRIBUTING[^/]*|ARCHITECTURE[^/]*|CHANGELOG[^/]*|CONTEXT\.md|AGENTS\.md|CLAUDE\.md|GEMINI\.md|copilot-instructions\.md|[^/]+\.instructions\.md|[^/]+\.agent\.md|SKILL\.md)$' "$list" \
  | awk -F/ 'NF <= 4' | head -30 | bullets
for d in docs doc; do
  n=$(grep -c "^$d/" "$list")
  [ "$n" -gt 0 ] && echo "- $d/: $n files"
done
# Decision records, wherever they live.
grep -E '(^|/)(adr|adrs|decisions)/[^/]+\.md$' "$list" | sed 's|/[^/]*$||' | sort | uniq -c \
  | sed -E 's/^ *([0-9]+) (.*)$/- \2\/: \1 decision records/'

# Packs that agd installed ("pack <source> <pack>" lines), one line per source, to compare with the stack.
section "Installed packs (.agd.lock)"
if [ -f .agd.lock ]; then
  packs=$(awk '$1 == "pack" && NF == 3 {
    if (!($2 in p)) order[++n] = $2
    p[$2] = p[$2] (p[$2] != "" ? ", " : "") $3
  }
  END { for (i = 1; i <= n; i++) print "- " order[i] ": " p[order[i]] }' .agd.lock)
  if [ -n "$packs" ]; then printf '%s\n' "$packs"; else echo "None listed in .agd.lock."; fi
else
  echo "None: no .agd.lock, so agd doesn't manage this project."
fi

if [ "$is_git" = 1 ]; then
  section "Recent commits"
  recent=$(git log -12 --format='- %ad %s' --date=short 2>/dev/null)
  if [ -n "$recent" ]; then printf '%s\n' "$recent"; else echo "No commits yet."; fi

  section "Most changed files, last 200 commits"
  hot=$(git log -200 --format= --name-only 2>/dev/null | grep -v '^$' | sort | uniq -c | sort -rn | head -10)
  if [ -n "$hot" ]; then printf '%s\n' "$hot" | counted; else echo "No commits yet."; fi
fi

section "Local notes (.local_context/, not committed)"
if [ -d .local_context ]; then
  if [ "$is_git" = 1 ] && ! git check-ignore -q .local_context/__probe__ 2>/dev/null; then
    echo "WARNING: .local_context/ is not git-ignored. Its contents could be committed."
    echo
  fi
  found=$(find .local_context -type f ! -path .local_context/.gitignore ! -path .local_context/README.md | head -30)
  if [ -n "$found" ]; then printf '%s\n' "$found" | bullets; else echo "Empty."; fi
else
  echo "None."
fi
