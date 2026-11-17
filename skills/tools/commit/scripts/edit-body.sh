#!/usr/bin/env bash
# Replaces an open pull request's description with the body read from stdin.
# An empty body stops it: a read that failed upstream must never erase the description.
# Usage: edit-body.sh <worktree> <pr url> < body
set -euo pipefail
usage="usage: edit-body.sh <worktree> <pr url> < body"
wt="${1:?$usage}"
pr="${2:?$usage}"
stop() { echo "STOP: $1" >&2; exit 1; }

case "$pr" in
  https://github.com/*/pull/*) ;;
  *) stop "give the pull request's URL, not \"$pr\"" ;;
esac
git -C "$wt" rev-parse --show-toplevel >/dev/null 2>&1 || stop "$wt is not inside a git worktree"
body=$(cat)
[ -n "$(printf '%s' "$body" | tr -d '[:space:]')" ] || stop "the body is empty: the description was left as it is"

cd "$wt"
printf '%s\n' "$body" | gh pr edit "$pr" --body-file - >/dev/null
echo "$pr"
