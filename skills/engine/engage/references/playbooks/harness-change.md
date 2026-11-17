Before anything else, read these principles:

- ../../../../principles/principle-concept-not-case/SKILL.md
- ../../../../principles/principle-encode-lessons-in-structure/SKILL.md

Build a hook, script, eval or test suite only when a step of a run uses it.

The harness is the user's config folder, `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`, plus the project's
`.claude/`. A file of the geovane plugin (its path holds `plugins/cache/`)
is not the user's to edit: an update overwrites it. For such a file, write the change as a diff with
its reason and suggest a pull request to the plugin's own repo; nothing else in this
playbook runs on it.

1. Run `../../scripts/harness-read.sh <file>`: it prints the
   file and every harness file that names it. Read those too.
2. A fix the evidence settles (a broken link, a fact the code disproves, a contradiction with a rule
   the user set) goes to step 3. Any other change:
   - Write it to a copy in the scratchpad.
   - Run the `geovane:cleaner` agent once on the copy.
   - Show the user what changes as scenarios on a real case (what happens today, what happens
     after, each row tested or inferred), who reads it and at which step, and why a script, a hook
     or a gate cannot carry it before text does. Text the user must approve goes whole, as it will
     be written to the file; never a diff.
   - Apply it only after the user agrees. Without the user in the conversation, trail it as a
     `harness` note with the diff whole, and stop here.
3. Apply it. When the file is a principle, update its line in
   `../../references/principles.md`. Check that every file,
   skill, agent and script it names exists, and grep the old phrase so no file still says it.
4. Run the `geovane:cleaner` agent on the edited files, once, after the last edit, unless
   step 2 ran it on this text.
5. When the change alters what an agent, a skill or a hook does, test it in a fresh process:
   `claude -p`, a new spawn, or a hook fed a sample input. Send to `trash` what the test left,
   including its folders under `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/projects/`.

**Reply:** what changed and why, as the scenarios of step 2, the cleaner's result and the test's result.
