#!/usr/bin/env bash
# Resolves a review thread, by the `thread` id that watch-pr.sh prints.
set -euo pipefail
gh api graphql -f id="$1" -f query='
  mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }' \
  -q .data.resolveReviewThread.thread.isResolved
