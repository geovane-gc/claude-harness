---
name: how
description: "Use for \"how does X work\", code walkthroughs before changing something, and placement / ownership / layering questions (\"where should this live\", \"which package owns this\", \"is this the right layer\"). Explains subsystem architecture, runtime flow, onboarding mental models."
---

# How

You hand the question to a coordinator and read its answer. The coordinator is an `geovane:delegate`
on opus at medium effort: it sends explorers to read the code and writes the explanation. You
read no code for it.

The run folder is the one the caller names, or `${user_config.workspace}/.runs/how-<slug>/`
when it names none, `<slug>` naming the question in up to five words of kebab-case.

1. Fill `templates/request.md` and write it to `<run folder>/how/request.md`.
2. Spawn the coordinator with: "Read `${CLAUDE_PLUGIN_ROOT}/skills/tools/how/references/coordinator-prompt.md`
   and follow it. Your request is `<run folder>/how/request.md`."
3. Answer with the explanation's path. When a person asked the question, follow the path with the
   file's text unchanged. A step of a run decides from the answer and hands the path on; it opens
   the file only for a fact the answer lacks.
