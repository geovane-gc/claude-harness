#!/usr/bin/env bash
# PreToolUse[Bash] guard. Blocks only what cannot be undone and nothing else already stops: a force
# push (GitHub protects main, not a pull request's branch), any recursive rm, and a command that
# throws away uncommitted work. Each block says the recoverable way. It also stops an engineer's own
# `git commit`: the commit skill commits (its scripts run git inside, so they pass).
INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$CMD" ] && exit 0
AGENT=$(printf '%s' "$INPUT" | jq -r '.agent_type // empty')
# A plugin hook fires in the whole session; this guard is only for the plugin's own agents.
case "$AGENT" in
  geovane:*) ;;
  *) exit 0 ;;
esac

deny() {
  printf '%s\n' "$1" >&2
  exit 2
}

GIT='^git([[:space:]]+-[Cc][[:space:]]+[^[:space:]]+)*[[:space:]]+'
KEEP="Use 'git stash push -- <paths>' instead: it clears the same changes, and 'git stash pop' brings them back. The blocked command stays blocked after the stash."

# One line per simple command, split at ; & | and newlines. Only a command that starts with git, rm
# or sudo rm can match a rule below, so the rest is dropped here, which keeps a long command inside
# the hook's 10 s limit.
SEGMENTS=$(printf '%s\n' "$CMD" | sed -E 's/(\|\||&&|;|\||&)/\n/g' | sed -E 's/^[[:space:]]+//' \
  | grep -E '^(git[[:space:]]|(sudo[[:space:]]+)?rm[[:space:]])')
[ -z "$SEGMENTS" ] && exit 0

while IFS= read -r seg; do
  if printf '%s' "$seg" | grep -qE "${GIT}push([[:space:]]|$)" \
    && printf '%s' "$seg" | grep -qE '[[:space:]](--force|--force-with-lease|--force-if-includes)([[:space:]=]|$)|[[:space:]]-[A-Za-z]*f[A-Za-z]*([[:space:]]|$)|[[:space:]]\+[^[:space:]]'; then
    deny "BLOCKED: force push is never allowed, on any branch, lease or not. Use plain 'git push'; to reconcile with the base, merge the base into the branch. If only a force would succeed, stop and say so."
  fi
  if printf '%s' "$seg" | grep -qE '^(sudo[[:space:]]+)?rm[[:space:]]' \
    && printf '%s' "$seg" | grep -qE '[[:space:]](-[A-Za-z]*[rR][A-Za-z]*|--recursive)([[:space:]]|$)'; then
    deny "BLOCKED: 'rm -r' deletes for good. Use 'trash <path>' (/usr/bin/trash): it moves the folder to the Trash, where it can be restored. Name each path literally; never build it from a variable or a command's output."
  fi
  if printf '%s' "$seg" | grep -qE "${GIT}reset([[:space:]].*)?[[:space:]]--hard([[:space:]]|$)"; then
    deny "BLOCKED: 'git reset --hard' throws away uncommitted work for good. $KEEP To move the branch to a commit, stash and then run 'git reset --keep <commit>'."
  fi
  if printf '%s' "$seg" | grep -qE "${GIT}checkout([[:space:]]|$)" \
    && printf '%s' "$seg" | grep -qE '[[:space:]](--|-f|--force)([[:space:]]|$)'; then
    deny "BLOCKED: 'git checkout -- <path>' or '-f' throws away uncommitted work for good. $KEEP"
  fi
  if printf '%s' "$seg" | grep -qE "${GIT}restore([[:space:]]|$)" \
    && { ! printf '%s' "$seg" | grep -qE '[[:space:]](--staged|-S)([[:space:]]|$)' \
      || printf '%s' "$seg" | grep -qE '[[:space:]](--worktree|-W)([[:space:]]|$)'; }; then
    deny "BLOCKED: 'git restore <path>' throws away uncommitted work for good ('--staged' alone only unstages). $KEEP"
  fi
  if printf '%s' "$seg" | grep -qE "${GIT}switch([[:space:]].*)?[[:space:]](--discard-changes|-f|--force)([[:space:]]|$)"; then
    deny "BLOCKED: 'git switch --discard-changes' throws away uncommitted work for good. $KEEP"
  fi
  if printf '%s' "$seg" | grep -qE "${GIT}clean([[:space:]]|$)" \
    && printf '%s' "$seg" | grep -qE '[[:space:]](-[A-Za-z]*f[A-Za-z]*|--force)([[:space:]]|$)'; then
    deny "BLOCKED: 'git clean -f' deletes untracked files for good. List them with 'git clean -n' and move what you no longer need to a scratch folder instead."
  fi
  if [ "$AGENT" = geovane:engineer ] && printf '%s' "$seg" | grep -qE "${GIT}commit([[:space:]]|$)"; then
    deny "BLOCKED: an engineer does not run 'git commit'. Leave the change uncommitted in the worktree and report it: the commit skill commits it, one commit per thing, and pull requests are squash-merged. Show a test's red then green with its failing run before the code and its passing run after, in your answer. When your brief says to commit, invoke the commit skill with the worktree."
  fi
done <<< "$SEGMENTS"

exit 0
