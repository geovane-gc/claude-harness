---
name: what
description: >-
  Restates the last answer in plain words for a reader who did
  not follow it: shorter, without jargon, with an example and
  color where they help.
disable-model-invocation: true
---
Restate your last message the way one person explains it to
another.

- Shorter than the original, in the user's language, with each
  thing called by its everyday name instead of jargon.
- Keep its point, and its question if it asked one; drop the rest.
- Only when it leaves the user something to decide: say in one
  line what is being decided, then list the choices numbered
  (1., 2., 3.). Each choice is one line saying what happens if
  they pick it. Mark the one you recommend, with the reason in a
  few words. End by asking which number.
- Add one example, from the user's own work when there is one.
- When the message is about code, show the code it explains, cut
  to the lines that matter, with its `file:line`. The example is
  code too: the same lines with real values, or the lines before
  and after the change.
- Mark meaning with color: ✅/❌ for right and wrong, 🟩🟦🟨🟥
  for options or roles, a diff block for before and after.
