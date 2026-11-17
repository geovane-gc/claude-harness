---
name: principle-cost-aware
description: "Apply before every tool call and every request to an agent. Everything costs tokens: each turn re-sends the whole context and each request is worked out in full, so do the job in few turns and ask for what the next decision needs."
disable-model-invocation: true
---

# Cost-Aware

Everything costs tokens. Spend them on what the next decision needs.

**Why:** every turn re-sends the whole context, so a job costs in proportion to its turns; and an
agent works out everything a request names, so a request costs in proportion to what it asks for.

**Pattern:**
- **Read in batches:** print every file a step needs in one Bash call, starting with all the files
  the task names. Read a file whole.
- **Search in one pass:** one grep with every pattern at once.
- **Independent calls in one turn:** reads, searches and lookups that do not depend on each other go
  in the same message.
- **Record with the action:** send a trail note, a task update or a log line in the same message as
  the call it records.
- **Ask only for what you know is needed:** each thing you ask for is something you are confident
  the next decision uses, asked concretely enough that one answer settles it. A vague or
  just-in-case ask ("the whole flow", "anything related", "e.g. other flows") is worked out in full
  and paid in full.
- **When unsure, name the decision instead:** say who uses the answer and the decision it feeds, and
  let the agent work out what it needs, rather than listing guesses.
- **Give what you know:** hand over what you already read or measured, with its source, so no one
  finds it again.
- **Give only what the job uses:** pass the files the job reads.
