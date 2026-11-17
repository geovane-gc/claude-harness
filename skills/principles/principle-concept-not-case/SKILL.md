---
name: principle-concept-not-case
description: "Apply when writing text an agent will read: a skill, an agent, a rule, a CLAUDE.md or a knowledge base file. State the general idea, not the case that taught it."
disable-model-invocation: true
---

# Concept, Not Case

State the general idea first. A list reads as the closed set of what is allowed, and the agent stops at it; the concept lets it handle what the list did not foresee.

- Keep a list only when the set is truly closed.
- A concrete case can be an example, never the boundary of the rule.
- Leave out names that change: partners, callers, classes, ticket ids and current-state facts.
- Before writing a sentence, ask whether it holds, word for word, for every case the text covers.
- Write only what the agent would get wrong on its own, cannot see in the code, or would cost a lot if wrong.
