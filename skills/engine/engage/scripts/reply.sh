#!/usr/bin/env bash
# Replies to a review comment. The reply text comes from a file, never from the command line.
set -euo pipefail
pr="$1"
comment="$2"
file="$3"
read -r repo number < <(gh pr view "$pr" --json url,number -q '[(.url | split("/")[3:5] | join("/")), .number] | @tsv')
jq -n --rawfile body "$file" '{body: $body}' |
  gh api --method POST "repos/$repo/pulls/$number/comments/$comment/replies" --input - -q .html_url
