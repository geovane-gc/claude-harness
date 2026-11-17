#!/usr/bin/env bash
# Prints what the commit skill decides from, one key=value per line.
# Usage: state.sh <worktree>
# The worktree is always named: the shell's current folder may be another session's work.
wt="${1:?usage: state.sh <worktree>: name the worktree to commit; the current folder is never used}"
here=$(cd "$(dirname "$0")" && pwd)  # before the cd: $0 may be relative
cd "$wt" 2>/dev/null && cd "$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "STOP: $wt is not inside a git worktree" >&2; exit 1; }
default=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
[ -z "$default" ] && default=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null)
[ -z "$default" ] && default=main
branch=$(git branch --show-current)
# The branch the worktree was made from: its upstream until the first push, else the default.
base=$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null | sed 's|^origin/||')
{ [ -z "$base" ] || [ "$base" = "$branch" ]; } && base=$default
changes=$(git status --porcelain | wc -l | tr -d ' ')
ahead=$(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo no-upstream)
pr=none; pr_title=; pr_url=
if [ "$branch" != "$default" ] && json=$(gh pr view "$branch" --json state,title,url 2>/dev/null); then
  pr=$(jq -r .state <<<"$json" | tr '[:upper:]' '[:lower:]')
  pr_title=$(jq -r .title <<<"$json")
  pr_url=$(jq -r .url <<<"$json")
fi
# Use the repo's own pull request template when it has one, else the skill's.
root=$(git rev-parse --show-toplevel)
template=$here/../templates/pr.md
for candidate in .github/PULL_REQUEST_TEMPLATE.md .github/pull_request_template.md; do
  [ -f "$root/$candidate" ] && { template=$root/$candidate; break; }
done
printf 'worktree=%s\ndefault=%s\nbase=%s\nbranch=%s\nchanges=%s\nahead=%s\npr=%s\npr_title=%s\npr_url=%s\ntemplate=%s\n' \
  "$root" "$default" "$base" "$branch" "$changes" "$ahead" "$pr" "$pr_title" "$pr_url" "$template"
