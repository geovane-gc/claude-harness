---
name: agent-evolve
description: Improve the owner's Slack agent (installed from this plugin's agent/ folder) or build a new routine, tool or task prompt for it from its backlog and daily reviews. Use when the owner asks to work on their agent, on an item of its backlog, on something decided in its control channel, or to debug an agent failure.
---
Home: $AGENT_HOME (read README.md, CONVENTIONS.md, pepper/SPEC.md when it exists; knowledge at knowledge/INDEX.md).

## 1. Pick the work
- `$AGENT_HOME/bin/backlog list open`, the last daily review in the control channel (and the owner's answers in its
  thread), error threads in the control channel, `pepper/logs/watch.log`, today's `pepper/state/events/<date>.jsonl`.
- One item at a time. With the owner in the session: one decision per question, recommendation first.

## 2. Build where it belongs (CONVENTIONS.md)
- The agent's behavior: `pepper/` (watch.py, lib/, skills/<task>/SKILL.md = system prompts of lean `claude -p` runs).
  Helpers: `bin/`. Knowledge: `knowledge/`. Install values: `pepper/config.json`.
- `plugin/` is a link to the agent's clone of geovane-gc/claude-harness: never edit it there. A change to the harness
  (engage, this skill) or to the agent folder every install starts from (`agent/` in that repo) is a pull request on
  geovane-gc/claude-harness, through `/geovane:commit`.
- Security is not optional: knowledge/security-policy.md (send guard, no credentials, no environment access, Slack
  Connect blocked). After changing `pepper/guard/`, run `/usr/bin/python3 -m unittest pepper/guard/test_guards.py`.
- Prefer code (Python stdlib, /usr/bin/python3) for anything deterministic; tokens only where judgment is needed.
  Measure the cost of any new `claude -p` path (events.jsonl records cost).
- What differs between owners (orgs, hosts, channels, service names) is a config value, never a literal in code or
  prompts.

## 3. Prove it
- `/usr/bin/python3 pepper/watch.py --dry --since <minutes>` on real traffic; unit-test parsers on real tool output.
- For a new run type, run it once by hand and read its JSONL log; check the control channel for what it posted.
- Never claim done without evidence.

## 4. Close the loop
- `bin/backlog done <id> "<what changed, commit>"`; update pepper/SPEC.md and knowledge when facts changed.
- Commit in $AGENT_HOME (`git -c user.name=Claude -c user.email=claude@localhost commit -- <files>`), naming the files.
- A change that every install should get goes to `agent/` in geovane-gc/claude-harness too, by pull request.
- Tell the owner in the control channel (one line with the agent's prefix) when a change affects how the agent behaves.

## Code knowledge comes out of here, it doesn't live here
When the same kind of code work shows up twice, encode it where it is read: a repo's rule in that repo's CLAUDE.md or
REVIEW.md, a way of working in an engage playbook. Never in this skill.
