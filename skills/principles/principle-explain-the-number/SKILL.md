---
name: principle-explain-the-number
description: "Apply before you trust, report, or act on a number you measured: a count, a status code, a test total, or an eval result. Rule out that it measured something other than the work you think."
disable-model-invocation: true
---

# Explain the Number

- List what else the number could be measuring, and rule out each one with evidence. The usual suspects are errors, skipped or cached work, code that never ran, an untuned side (one left on default settings), noise, and a piece too small to matter end to end.

For an eval result, ask the same of the trials: did every run do the task, does the gap hold across trials and models, and does the scenario matter.

You skipped this when you report a number without saying what you ruled out.

Distinct from [Prove It Works](../principle-prove-it-works/SKILL.md), which checks that an output is real.
