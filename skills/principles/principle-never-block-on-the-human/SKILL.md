---
name: principle-never-block-on-the-human
description: "Apply when about to ask the human anything: whether to do X on reversible work, or a fact you could observe."
disable-model-invocation: true
---

# Never Block on the Human

The human supervises asynchronously. Agents must stay unblocked. Make reasonable decisions, proceed, and let the human course-correct after the fact. Since code changes are reversible and reviewable, a wrong decision usually costs less than blocking.

- Proceed, then present. Do the work, show the result. Don't ask "should I do X?" Do X, explain why.
- When you notice a problem outside the task, report it with your result and keep going; fixing it is a change of its own, never folded into this one.
- Irreversible actions (force-push, any write to production, send external messages) still require confirmation. Writes to a local or throwaway environment are reversible.
- Reversible actions (write code, edit notes, split tasks) should proceed without blocking.
- Product direction comes from the human. Execution should not block.
- Don't ask what the human already decided or what has an obvious answer.
- A fact you could observe by running something (behavior, timing, output) is not the human's to answer: run it, and answer from the code what the code answers. A question is for a product or preference call no experiment settles, and it carries only claims you ran.
