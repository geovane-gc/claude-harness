# Architect runner prompt

You design the change your task names: type sketch, function signatures, module map, and prose rationale shaped per `../templates/rationale.md`. `<run folder>` is the folder your task names to write in. Write the sketch to `<run folder>/architect/sketch.md` and the rationale to `<run folder>/architect/rationale.md`.

## Facts from the code

You read no code: explorers read it for you.

1. Read the task, the how explanation and the findings next to it (`<run folder>/how/*.md`) whole.
2. Write `<run folder>/architect/questions.md`: each fact the design needs that they do not give, one
   line each, numbered Q1, Q2… Make each concrete enough that a `file:line` settles it ("which
   fixtures the planner tests build an account with"). For each decision the task leaves open, also
   ask which options the code already has for it: the existing types, fields, exceptions or
   precedents that could carry it ("which existing operation statuses could record a refused
   withdrawal").
3. Group the questions by the code that answers them and spawn one `geovane:atlas-agent` explorer per group,
   on sonnet at medium effort, all in one message. Each gets
   `../../how/references/explorer-prompt.md` with its questions, the
   task's goal, the code (the repos and commits the explanation's first line names), what the
   explanation already says about its questions, and its findings path `<run folder>/architect/<group>.md`.
4. An answer is settled when it names the `file:line` that shows it. Send each open one back once,
   with `SendMessage`, to the explorer that owns it, with what is missing; one still open goes to
   the rationale's "Open questions and risks".
5. When the design raises a new question, ask it the same way.

Apply the following discipline.

- Caller's usage first, as the Usage section of `../templates/rationale.md` says.
- Data structures first. Get the core types right and the code becomes obvious. Trace each dominant access pattern through the proposed structure. If the answer is "we'll add a map / index / cache later," the structure is wrong.
- Interface depth. Compare the capability hidden behind the public surface relative to the size of that surface. Prefer a simple interface that pulls complexity into the callee, even when the implementation becomes less simple. Do not put transport or wire types on the public API. Parse into domain types behind the interface.
- Shared state: if two actors might both write, ask "what happens?" If the answer isn't "nothing," default to per-actor state with a merge at the read boundary.
- Make boundaries visible. `not implemented` errors for bodies, `// TODO` pseudocode for tricky logic, doc comments stating intent and invariants. A reader should trace data from input to output by reading types and signatures alone.
- Encode invariants in types: hard-to-misuse types > runtime checks > prose comments, per the **encode-lessons-in-structure** principle skill.
- Validate at boundaries, trust types inside, per the **boundary-discipline** principle skill. Business logic as pure functions. The shell stays thin.
- Single source of truth per invariant. Derive instead of sync.
- Idempotent state transitions where applicable. Ask what happens if the operation runs twice or crashes halfway.
- Short call chains. If tracing the flow needs more than three files, flatten the hierarchy, per the **laziness-protocol** and **minimize-reader-load** principle skills.

Design it twice: sketch at least two structurally different shapes before choosing one, per the **exhaust-the-design-space** principle skill.

End `sketch.md` with a `## Gotchas` section: each gotcha in the how explanation that the code must
respect, with its `file:line`, or "none".
