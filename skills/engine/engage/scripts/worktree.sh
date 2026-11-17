#!/usr/bin/env bash
# Prepares a task's worktree from <base>, the repo's default branch when left out, and prints its path.
# Usage: worktree.sh <repo> <branch> [<base>]
# <repo> is a path, or the name of a repo under $WORKSPACE. <base> is a branch name; origin/<base> works too.
# Stops (exit 1) when the branch exists locally or on origin, or the worktree path already exists.
set -euo pipefail
src="$1"
[ -d "$src" ] || src="${WORKSPACE:?set WORKSPACE to the folder that holds the repos, or give the path of the repo}/$1"
repo="$(git -C "$src" rev-parse --show-toplevel)"
branch="$2"
path="$repo/.claude/worktrees/${branch##*/}"
base="${3:-$(git -C "$repo" ls-remote --symref origin HEAD | sed -n 's#^ref: refs/heads/\(.*\)	HEAD$#\1#p')}"
base="${base#origin/}"
git -C "$repo" fetch -q --prune origin "$base"
if git -C "$repo" show-ref --verify --quiet "refs/heads/$branch"; then
  echo "STOP: branch $branch already exists locally: an earlier run left it." >&2; exit 1
fi
if git -C "$repo" ls-remote --exit-code --heads origin "$branch" >/dev/null 2>&1; then
  echo "STOP: branch $branch already exists on origin: an earlier run left it." >&2; exit 1
fi
if [ -e "$path" ]; then
  echo "STOP: $path already exists: an earlier run left it." >&2; exit 1
fi
git -C "$repo" worktree add -q "$path" -b "$branch" "origin/$base"
echo "$path"
