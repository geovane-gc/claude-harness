#!/usr/bin/env bash
# Merges a pull request's base into its branch, in the branch's worktree, unless the merge conflicts: then it
# lists the files that conflict.
# Never pushes, and never leaves a merge half done.
# Usage: merge-base-in.sh <pr url> <worktree>
#
# A parent pull request merged by squash leaves on the base a commit (the twin) with the same files as a commit
# of this branch. A plain merge then conflicts on every hunk both sides changed, though the base holds
# nothing the branch lacks. The twin is merged with `-s ours`: the branch's files are the result. A base
# commit counts as a twin only when the branch and the base have a single merge base and the branch's
# matching commit descends from it; otherwise `-s ours` could drop a change of the base.
#
# The first word of the output, and the exit code:
#   UP_TO_DATE  0  the base is already in the branch; the line says when commits still wait for a push
#   SAME_TREE   0  the base's last commit is a twin: merged, the branch's files unchanged
#   MERGED      0  the base merged with no conflict, after its twin when it has one
#   CONFLICTS   2  the files that conflict, one per line; they are not merged. A twin before them is.
#   STOP        1  the script stopped; the rest of the line says why
set -euo pipefail
usage="usage: merge-base-in.sh <pr url> <worktree>"
pr="${1:?$usage}"
wt="${2:?$usage}"
stop() { echo "STOP: $1" >&2; exit 1; }
g() { git -C "$wt" "$@"; }
short() { g rev-parse --short "$1"; }

case "$pr" in
  https://github.com/*/pull/*) ;;
  *) stop "give the pull request's URL, not \"$pr\": a number alone means a different pull request in each repo" ;;
esac
g rev-parse --show-toplevel >/dev/null 2>&1 || stop "$wt is not inside a git worktree"
repo=$(printf '%s' "$pr" | sed -E 's#https://github.com/([^/]+/[^/]+)/pull/.*#\1#')
case "$(g remote get-url origin)" in
  *"$repo"|*"$repo.git") ;;
  *) stop "$wt is a checkout of $(g remote get-url origin), not of $repo" ;;
esac
read -r base head <<<"$(gh pr view "$pr" --json baseRefName,headRefName -q '"\(.baseRefName) \(.headRefName)"')"
[ -n "$base" ] && [ -n "$head" ] || stop "could not read the base and the branch of $pr"
branch=$(g branch --show-current)
[ "$branch" = "$head" ] || stop "$wt is on \"$branch\", and the pull request's branch is \"$head\""
[ -z "$(g status --porcelain)" ] || stop "$wt has uncommitted changes: commit them or put them away first"

g fetch -q origin "$base" "$head"
if ! g merge-base --is-ancestor "origin/$head" HEAD; then
  g merge-base --is-ancestor HEAD "origin/$head" \
    || stop "$branch and origin/$head each have commits the other lacks: settle that first"
  g merge -q --ff-only "origin/$head"
fi

tip=$(short "origin/$base")
if g merge-base --is-ancestor "origin/$base" HEAD; then
  ahead=$(g rev-list --count --first-parent "origin/$head..HEAD")
  note=""; [ "$ahead" = 0 ] || note=" $ahead of the branch's commits are not pushed: push them with the commit skill."
  echo "UP_TO_DATE: origin/$base ($tip) is already in $branch.$note"
  exit 0
fi

# The twin: the newest commit only the base has whose files equal those of a commit only the branch has.
twin=""; like=""
bases=$(g merge-base --all HEAD "origin/$base")
if [ -n "$bases" ] && [ "$(printf '%s\n' "$bases" | wc -l | tr -d ' ')" = 1 ]; then
  mine=$(g log --ancestry-path --format='%T %H' "$bases..HEAD")
  while read -r commit tree; do
    like=$(awk -v t="$tree" '$1 == t { print $2; exit }' <<<"$mine")
    if [ -n "$like" ]; then twin=$commit; break; fi
  done < <(g log --first-parent --format='%H %T' "HEAD..origin/$base")
fi

said=""
if [ -n "$twin" ]; then
  before=$(g rev-parse HEAD)
  g merge -q -s ours --no-edit \
    -m "Merge remote-tracking branch 'origin/$base' into $branch" \
    -m "$(short "$twin") on $base, a squash merge, has the same files as $(short "$like") of this branch. Merged with -s ours: the branch's files do not change." \
    "$twin" || { g merge --abort 2>/dev/null || true; stop "git could not write the merge commit"; }
  g diff --quiet "$before" HEAD || stop "the -s ours merge changed files, which cannot be: look at $wt"
  said="$(short "$twin") on origin/$base has the same files as $(short "$like") of this branch: merged with -s ours as $(short HEAD), the branch's files unchanged."
  if g merge-base --is-ancestor "origin/$base" HEAD; then
    echo "SAME_TREE: $said Not pushed."
    exit 0
  fi
fi

# What is left of the base, tried without touching the worktree.
set +e
tried=$(g merge-tree --write-tree --name-only --no-messages HEAD "origin/$base" 2>&1); code=$?
set -e
case "$code" in
  0)
    before=$(g rev-parse HEAD)
    g merge -q --no-edit "origin/$base" || { g merge --abort 2>/dev/null || true; stop "git could not write the merge commit"; }
    changed=$(g diff --name-only "$before" HEAD | wc -l | tr -d ' ')
    echo "MERGED: ${said:+$said }origin/$base ($tip) merged with no conflict as $(short HEAD): $changed files changed. Not pushed."
    ;;
  1)
    files=$(printf '%s\n' "$tried" | sed 1d | sed '/^$/d' | sort -u)
    echo "CONFLICTS: merging origin/$base ($tip) conflicts in $(printf '%s\n' "$files" | wc -l | tr -d ' ') files; they are not merged.${said:+ $said Not pushed.}"
    printf '%s\n' "$files"
    exit 2
    ;;
  *) stop "git merge-tree failed: $tried" ;;
esac
