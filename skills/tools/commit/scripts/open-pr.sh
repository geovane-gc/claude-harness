#!/usr/bin/env bash
# Opens the worktree's pull request, ready for review. The body comes on stdin.
# Usage: open-pr.sh <worktree> <base> "<title>"
# The worktree is always named: the shell's current folder may be another session's work.
# Every Verification bullet names how it is known: (measured: ...), (inferred: ...) or (guess),
# and so does every Assumptions bullet, or says (not run).
set -euo pipefail
wt="${1:?usage: open-pr.sh <worktree> <base> \"<title>\": name the worktree; the current folder is never used}"
here=$(cd "$(dirname "$0")" && pwd)  # before the cd: $0 may be relative
cd "$wt" 2>/dev/null && cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "STOP: $wt is not inside a git worktree" >&2; exit 1; }
base="${2:?usage: open-pr.sh <worktree> <base> \"<title>\"}"
title="${3:?usage: open-pr.sh <worktree> <base> \"<title>\"}"
"$here/check-title.sh" "$title"
body=$(cat)

problems=$(BODY="$body" python3 - <<'EOF'
import os, re

body = os.environ["BODY"]
MARK = r"\((measured|inferred): [^)]|\(guess\)"

def section(text, name):
    m = re.search(rf"^## {name}\s*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return [l.strip()[2:].strip() for l in (m.group(1) if m else "").splitlines() if l.strip()[:2] in ("- ", "* ")]

for b in section(body, "Verification"):
    if not re.search(MARK, b):
        print(f"Verification, no mark: {b}")
for b in section(body, "Assumptions"):
    if not re.search(MARK + r"|\(not run(: [^)]+)?\)", b):
        print(f"Assumptions, no mark: {b}")
EOF
)
if [ -n "$problems" ]; then
  echo "BLOCKED: fix the body and run this again:" >&2
  echo "$problems" >&2
  echo "Marks: (measured: <the check>), (inferred: <what you read>), (guess); an Assumption may be (not run) or (not run: <why>)." >&2
  exit 1
fi
deps=$(printf '%s' "$body" | "$here/deps.sh")
while read -r dep condition; do
  [ -z "$dep" ] && continue
  if [ -z "$condition" ]; then
    echo "BLOCKED: Depends on $dep says what this pull request waits for: (needs it merged) or (needs it deployed in <env>). It is not the dependency's state today." >&2
    exit 1
  fi
  if [ "$(gh pr view "$dep" --json state -q .state)" = "CLOSED" ]; then
    echo "BLOCKED: $dep was closed without a merge; name the pull request that replaced it" >&2
    exit 1
  fi
done <<< "$deps"
# Each dependency names this pull request back, so the chain shows from either end.
link_back() {
  while read -r dep condition; do
    [ -z "$dep" ] && continue
    gh pr comment "$dep" --body "Depended on by $1: it needs this one $condition." >/dev/null
  done <<< "$deps"
}
# GitHub often fails on the first try. Before each try, look for the pull request first, so a
# create that went through but answered with an error never opens a second one.
branch=$(git branch --show-current)
for _ in 1 2 3 4 5 6 7 8 9 10; do
  url=$(gh pr list --head "$branch" --state open --json url -q '.[0].url' 2>/dev/null || true)
  [ -n "$url" ] && { echo "$url"; exit 0; }
  if url=$(printf '%s' "$body" | gh pr create --base "$base" --title "$title" --body-file -); then
    link_back "$url"
    echo "$url"
    exit 0
  fi
  sleep 30
done
echo "pull request create failed 10 times in a row" >&2
exit 1
