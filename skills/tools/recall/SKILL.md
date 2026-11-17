---
name: recall
description: >-
  Rebuilds where a topic stands from the user's past conversations
  and memories, checks its PRs, branches and tickets as they are
  now, and hands back a short brief.
argument-hint: "<topic> [window]"
disable-model-invocation: true
---
Rebuild where `$ARGUMENTS` stands, in the last 30 days unless it
names a window; with no topic, ask for one.

1. Find the conversations: `grep -l -i` the topic in
   `~/.claude/projects/*/*.jsonl` changed in the window, except
   this one and `*private-tmp*`; read the memories that mention it.
2. Read the matching parts with agents, a few conversations each.
   Each returns, per file: the goal, the decisions, what stayed
   open, the user's corrections, and the PRs, branches, tickets.
3. Check each PR, branch and ticket now with `gh`, `git`, Linear.
4. Reply: up to 5 lines of summary; one line per thread tagged
   `[done]`, `[open PR #N]`, `[in progress <branch>]`, `[reverted]`
   or `[not started]`; the problems that came back; the next step.
