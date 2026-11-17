---
name: principle-follow-the-existing-pattern
description: "Apply before naming, placing or shaping anything new in code. Find the nearest existing analogue and copy its pattern instead of inventing a variant."
disable-model-invocation: true
---

# Follow the Existing Pattern

Before adding anything, find how the code already does the same thing and copy that pattern exactly: name, constant, event type, file location, structure.

- Look for the nearest analogue first, open it, and mirror it.
- When a sibling service already solves the problem, copy its approach without asking the human to choose a variant, and state it in one line.
- A finer layout than the documented one is intent, not drift: keep it.
- When the human asks for a new design, the current code is input, not a constraint.
