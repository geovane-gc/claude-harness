---
name: reflect
description: >-
  Reviews a finished run of this session, the main conversation
  or one of its subagents, and reports what went right, what went
  wrong or was worked around, and whether the run used its skills
  and tools as written.
argument-hint: "[<descriptive text>]"
---

## 1. Find the run

Only runs of this session count. The main transcript is
`~/.claude/projects/*/"$CLAUDE_CODE_SESSION_ID".jsonl`; its
subagents are in the folder of the same name, under `subagents/`,
as `agent-<id>.jsonl` plus `agent-<id>.meta.json` (`agentType`,
`description`).

- no argument: the main transcript; inside an engage run, that run,
  with its run folder;
- a text: the subagent it describes, matched against each
  `agentType` and `description`; when several fit, the one whose
  `.jsonl` changed last.

Say which run it is in one line. No match: list this session's
subagents (type, description, time) and ask which.

## 2. Hand it to a fresh reader

Spawn one `geovane:delegate` in the foreground, with
`model: sonnet`, `effort: high`, the transcript path, the run
folder's `trail.md` and `cost.md` when it has them, and steps 3
and 4. With a `cost.md`, also give it the transcript of the
costliest subagent, the first entry other than `main` in the
`cost.md` Transcripts list, to review the same way. It edits nothing. Don't judge the run
yourself: you would defend what you did.

The transcript is long. The reader greps it for `is_error`,
`error`, `BLOCKED`, `FAILED`, the user's messages and each
`Skill`/`Read` of a skill file, and reads around the matches.
Tool results are the evidence, not the agent's own summary.

## 3. What the reader looks for

Answer three questions, each with a quote from a tool result:
- Did the run reach what it was asked? Name the check that
  proves it, or say the run only claimed it.
- What failed, and how was it worked around? A workaround is
  the main finding: the next run hits the same wall.
- Did it follow its skills and tools as written? Read each
  skill file the run opened and compare its steps with what the
  run did. A skill it should have opened and didn't counts too.

Then say where time and money went, such as a search repeated, a
fact the user typed that a tool could have fetched, or a long
output read whole. From `cost.md`, take the agents with the largest share and
the highest context peaks, and say for each whether its work
needed that much.

Before proposing a change, read the file it goes to. Already
said there: no proposal, unless the text is buried. Each
proposal names the file and the exact text, in this order: take
the wrong path away (a tool, a permission, the text it copied);
block it with a hook; catch it in a check that already runs; a
written rule last. At most five; a run that went well may have none.

## 4. Hand back

The reader returns this, and you save it as `<run folder>/reflect.md`
inside an engage run, otherwise as
`${user_config.workspace}/.runs/reflect-<date>/<agent id or main>.md`:

```markdown
# Reflection: <agentType or main>, <description>, <date>
Transcript: <path>
Reached what was asked: yes | no | unclear, <check or "only claimed">

### 1. <one line>
- What happened: <with ids and times>
- Evidence: "<quote>" (<where in the transcript>)
- Change: <file> (add | change): <exact text, old → new>
- Next run: <what it does differently>
```

Give the user the verdict line, the number of findings and the
path. Inside an engage run, that goes in the run's reply, and the
findings wait until the user asks for them. Then show one finding
per turn: the text as it is now and the suggested text. Write a change only after the
user's OK.
