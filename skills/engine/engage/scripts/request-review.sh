#!/usr/bin/env bash
# Asks Claude Code Review to review the whole pull request again, then waits up to two minutes
# for the new review to appear. Prints `queued` when it appears, or `running` when a review was
# already on its way (a repo set to review after every push starts one on the fix push by itself)
# or none appeared in time. Prints `limit`, and asks nothing, when the pull request already has two
# `@claude review` comments: past that, its threads wait for the human approver.
set -euo pipefail
pr="$1"
# Runs gh again when it fails, as the network often does; the tenth failure in a row ends the
# script with gh's own error.
gh_read() {
  for _ in 1 2 3 4 5 6 7 8 9; do
    gh "$@" 2>/dev/null && return
    sleep 30
  done
  gh "$@"
}
repo=$(gh_read pr view "$pr" --json url -q '.url | split("/")[3:5] | join("/")')
count=$(gh_read pr view "$pr" --json comments -q '[.comments[] | select(.body == "@claude review")] | length')
[ "$count" -ge 2 ] && { echo limit; exit 0; }
latest() {
  local sha
  sha=$(gh_read pr view "$pr" --json headRefOid -q .headRefOid) || return
  gh_read api "repos/$repo/commits/$sha/check-runs" \
    -q "[.check_runs[] | select(.name == \"Claude Code Review\")] | max_by(.id) // {id: 0, status: \"none\"} | .$1"
}
status=$(latest status)
[ "$status" = queued ] || [ "$status" = in_progress ] && { echo running; exit 0; }
before=$(latest id)
since=$(date -u +%Y-%m-%dT%H:%M:%SZ)
asked() {
  gh_read pr view "$pr" --json comments \
    -q "[.comments[] | select(.body == \"@claude review\" and .createdAt >= \"$since\")] | length"
}
# Posts `@claude review` up to 10 times, and only while none posted since this run began is on the
# pull request: a post that times out can still have gone through.
for _ in 1 2 3 4 5 6 7 8 9 10; do
  n=$(asked)
  [ "$n" -gt 0 ] && break
  gh pr comment "$pr" --body "@claude review" >/dev/null 2>&1 || sleep 30
done
n=$(asked)
[ "$n" -gt 0 ] || { echo "could not post @claude review: the network failed 10 times" >&2; exit 1; }
start=$(date +%s)
while true; do
  id=$(latest id)
  [ "$id" -gt "$before" ] && break
  [ $(($(date +%s) - start)) -gt 120 ] && { echo running; exit 0; }
  sleep 10
done
echo queued
