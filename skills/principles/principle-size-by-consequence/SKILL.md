---
name: principle-size-by-consequence
description: "Apply when deciding how much mechanism a risk deserves: a guard, a helper, a retry, a lock, a validation, a test. Size it by what happens when it fails, and by what the rest of the code already accepts, not by whether the risk can be imagined."
disable-model-invocation: true
---

# Size by Consequence

Every guard is code to read, test and keep. It earns its place by the failure it prevents.

- **Name the failure.** Before adding a mechanism, write what goes wrong without it, for whom, and
  how often. No concrete failure, no mechanism.
- **Match the house.** A risk the rest of the code already accepts in the same situation is
  accepted here too. A guard only this call site has is noise, or a gap everywhere else: say which.
- **Money gets the full weight.** Funds moved wrongly or twice, a widened permission, a lost message:
  these get the mechanism and the test (see `principle-record-before-side-effect`). A log line, a
  display string, an admin convenience does not.
- **No one-line helpers.** A function that wraps one call, used once, is a name for the reader to
  chase. Inline it.
- **Trust the types.** A null check the type rules out, or a validation the boundary already ran,
  is deleted, not added.
