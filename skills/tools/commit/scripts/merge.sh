#!/usr/bin/env bash
# Merges an approved pull request: brings the default branch in when the pull request is behind
# (the approval stays), then turns on squash auto-merge. Stops, saying why, when it cannot merge.
# The script merges a stack through its bottom pull request, the one on the default branch. It first
# folds (squash-merges) each pull request stacked on it into its base, from the top down, and only
# when every one has an approval. A default branch that dismisses approvals when a base changes then
# asks for one new approval, on the bottom one, instead of a new one per pull request.
# --without-approval skips both approval checks, for when the user said to merge without one: the
# author of a pull request cannot approve it, so one opened from the user's account has no approver
# but a teammate. The base branch's own rules still apply: GitHub holds the merge if they ask for one.
set -euo pipefail
pr="${1:?usage: merge.sh <pull request URL> [--without-approval]}"
without_approval=false
case "${2:-}" in
  "") ;;
  --without-approval) without_approval=true ;;
  *) echo "not merged: unknown option \"$2\"; the only one is --without-approval" >&2; exit 1 ;;
esac
case "$pr" in
  https://github.com/*/pull/*) ;;
  *) echo "not merged: give the pull request's URL, not \"$pr\": a number alone means a different pull request in each repo the shell may be in" >&2; exit 1 ;;
esac

url=$(gh pr view "$pr" --json url -q .url)
repo=$(printf '%s' "$url" | sed -E 's#https://github.com/([^/]+/[^/]+)/pull/.*#\1#')
default=$(gh repo view "$repo" --json defaultBranchRef -q .defaultBranchRef.name)
read -r decision state base <<< "$(gh pr view "$url" --json reviewDecision,mergeStateStatus,baseRefName \
  -q '"\(.reviewDecision // "" | if . == "" then "NONE" else . end) \(.mergeStateStatus) \(.baseRefName)"')"

# Prints the open pull requests stacked on a branch, the topmost first.
stacked_on() {
  gh pr list --repo "$repo" --base "$1" --state open --json url,headRefName -q '.[] | "\(.url) \(.headRefName)"' </dev/null |
    while read -r child head; do
      stacked_on "$head"
      echo "$child"
    done
}
if [ "$base" = "$default" ]; then
  stack=$(stacked_on "$(gh pr view "$url" --json headRefName -q .headRefName)")
  if [ -n "$stack" ]; then
    for child in $stack; do
      $without_approval && break
      approvals=$(gh pr view "$child" --json reviews -q '[.reviews[] | select(.state == "APPROVED")] | length')
      if [ "$approvals" -eq 0 ]; then
        echo "not merged: $child, stacked on $url, has no approval; nothing was folded"
        exit 1
      fi
    done
    for child in $stack; do
      gh pr merge "$child" --squash
      echo "folded $child into its base"
    done
    read -r decision state <<< "$(gh pr view "$url" --json reviewDecision,mergeStateStatus \
      -q '"\(.reviewDecision // "" | if . == "" then "NONE" else . end) \(.mergeStateStatus)"')"
  fi
fi

if [ "$decision" != "APPROVED" ] && ! $without_approval; then
  echo "not merged: $url is ${decision/#NONE/not reviewed}; it needs an approval first"
  exit 1
fi
# A dependency is merged first; a deploy it needs is a person's to confirm.
while read -r dep condition; do
  [ -z "$dep" ] && continue
  if [ "$(gh pr view "$dep" --json state -q .state)" != "MERGED" ]; then
    echo "not merged: $url depends on $dep, which is not merged"
    exit 1
  fi
  case "$condition" in
    "deployed in "*)
      echo "not merged: $url needs $dep $condition; confirm it and merge by hand"
      exit 1
      ;;
  esac
done <<< "$(gh pr view "$url" --json body -q .body | "$(dirname "$0")/deps.sh")"
# Stacked: the base is another open pull request's branch. A base with no pull request of its own is
# a long-lived branch the repo merges into, such as a deploy repo's environment branches (dev, staging, prod).
parent=$(gh pr list --repo "$repo" --head "$base" --state open --json url -q '.[0].url')
if [ -n "$parent" ]; then
  echo "not merged: $url is stacked on $parent; run merge.sh on the bottom of the stack, the pull request on $default, which folds this one into it"
  exit 1
fi
if [ "$state" = "DIRTY" ]; then
  echo "not merged: $url conflicts with $default; merge $default into its branch and push with the commit skill"
  exit 1
fi
if [ "$state" = "BEHIND" ]; then
  gh pr update-branch "$url"
  echo "brought $default into $url"
fi
gh pr merge "$url" --squash --auto
echo "auto-merge on: $url merges when its required checks pass"
