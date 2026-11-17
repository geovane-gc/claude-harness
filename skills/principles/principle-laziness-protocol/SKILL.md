---
name: principle-laziness-protocol
description: "Apply when refactoring, evaluating diff size, or tempted to add or remove abstractions, layers, or signal threading. Bias toward deletion and the smallest change that solves the problem."
disable-model-invocation: true
---

# Laziness Protocol

- **Consolidate decisions.** Do not repeat the same choice in several places. Put it behind one source of truth and pass the result as a simple flag.
- **Minimize the diff.** Make the smallest change that solves the problem. Fewer lines beat "elegant" boilerplate.
- **No new concepts first.** When a question exposes a flaw, answer with what already exists before adding a type, hook or name.
- **Solve this problem only.** Name an adjacent concern as its own item; do not fold it into this change.
- **Know what it buys before you delete it.** List what a type, layer or step does beyond carrying its inputs, and delete it only when nothing on that list is lost.
