#!/usr/bin/env bash
# Commits the worktree's change under the title, or only the paths given after it, then pushes the branch.
# Usage: ship.sh <worktree> "<title>" [path...]
# The worktree is always named: the shell's current folder may be another session's work.
set -euo pipefail
wt="${1:?usage: ship.sh <worktree> \"<title>\" [path...]: name the worktree to commit; the current folder is never used}"
here=$(cd "$(dirname "$0")" && pwd)  # before the cd: $0 may be relative
cd "$wt" 2>/dev/null && cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "STOP: $wt is not inside a git worktree" >&2; exit 1; }
title="${2:?usage: ship.sh <worktree> \"<title>\" [path...]}"
shift 2
"$here/check-title.sh" "$title"
if [ "$#" -gt 0 ]; then
  git add -- "$@"
  git commit -m "$title" -- "$@"
elif [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "$title"
fi
git push -u origin HEAD
