---
name: trail
description: Writes down, during a run, anything worth keeping about it (a decision, a fact learned, a problem found, something the docs lack, a skipped step, a harness change held for the user) in the run's one notes file. Use whenever something in a run is worth noting.
---

# Trail

A run keeps its notes in one file, `trail.md`, in its task folder,
`${user_config.workspace}/.runs/<task id or subject>/`. Write every note with
`${CLAUDE_PLUGIN_ROOT}/skills/engine/trail/scripts/trail.sh <task folder> <kind> "<text>"`, in the
same message as the action it records; a note about a result goes in the message of your next call.
A note never takes a call of its own, except the last notes before the run's reply. `trail.sh`
prints the note's id. Never write the file another way.

- `decision`: what you chose, because why.
- `fact`: what you learned, with (measured: the check and its output), (inferred: what you read) or
  (guess).
- `problem`: something wrong or to do outside the task, at where it is.
- `docs`: something the repo's `docs/` lacks or gets wrong, shown by the command or the line.
- `skip`: a playbook step you did not run, as copied into its task: why.
- `harness`: a harness change held for the user: the file; who reads it and at which step of a run; the
  file that already holds it, or none; what carries it, and why nothing earlier in script, hook,
  gate, text works; where the idea came from. Write the whole diff to a file and pass the file's path as the fourth argument, after the text.
- `info`: anything else about the run worth keeping.

When a note is settled later, add `trail.sh <task folder> settle <its id> "<how it ended>"`, such as
`→ COR-412` for a problem or `→ docs/flows.md` for a docs note.

Each line reads `<id> <HH:MM UTC> <kind> <text>`; grep it by kind.
