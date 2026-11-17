# Principles

Each line names a principle, when it applies and what it says. The full text is in
`../../../principles/principle-<name>/SKILL.md`.

- **attack-the-premise**: Apply when two or more fixes that share one premise have failed the same gate. Take a census of which actors hold the imbalance before the next fix, then question the premise instead of writing another fix that assumes it.
- **boundary-discipline**: Apply when wiring validation, error handling, or framework adapters. Concentrate guards at system boundaries (CLI, config, network, external APIs); trust internal types and keep business logic in pure functions.
- **build-the-lever**: Apply to any non-trivial work, not just bulk work: edits, migrations, analyses, checks. Build the tool that does it or proves it (codemod, script, generator, or a skill your subagents follow) instead of working by hand. The tool is the artifact a reviewer can rerun.
- **concept-not-case**: Apply when writing text an agent will read: a skill, an agent, a rule, a CLAUDE.md or a knowledge base file. State the general idea, not the case that taught it.
- **cost-aware**: Apply before every tool call and every request to an agent. Everything costs tokens: each turn re-sends the whole context and each request is worked out in full, so do the job in few turns and ask for what the next decision needs.
- **encode-lessons-in-structure**: Apply when a correction or an instruction you write could be enforced by a check. Encode the rule as a lint, metadata flag, runtime check, or script instead of more text.
- **exhaust-the-design-space**: Apply when facing a novel UI interaction or architectural decision with no precedent in the codebase. Build 2-3 competing prototypes and compare side by side before committing.
- **explain-the-number**: Apply before you trust, report, or act on a number you measured: a count, a status code, a test total, or an eval result. Rule out that it measured something other than the work you think.
- **fix-root-causes**: Apply when debugging. Trace each symptom to its root cause and fix it there; reproduce first, ask why until you reach it, resist nil-check guards that silence crashes.
- **follow-the-existing-pattern**: Apply before naming, placing or shaping anything new in code. Find the nearest existing analogue and copy its pattern instead of inventing a variant.
- **foundational-thinking**: Apply before writing logic: choosing core types and data structures, sequencing scaffold-vs-feature work, asking what concurrent actors share. Get the data structures right so downstream code becomes obvious.
- **guard-the-context-window**: Apply when context is filling up: large outputs, long files, repeated reads, fan-out planning. Route bulk to subagents; keep summaries in the main thread, not raw payloads.
- **laziness-protocol**: Apply when refactoring, evaluating diff size, or tempted to add abstractions, layers, or signal threading. Bias toward deletion and the smallest change that solves the problem.
- **make-operations-idempotent**: Apply when designing commands, lifecycle steps, or processing loops that run amid crashes, restarts, and retries. Converge to the same end state regardless of partial prior runs.
- **migrate-callers-then-delete-legacy-apis**: Apply when introducing a new internal API while old callers still exist. Migrate callers and delete the old API in the same wave instead of preserving compatibility layers.
- **keep-to-the-card**: Apply when the change grows past what the card asked: an extra hardening, a side behavior change, a review finding that widens the scope, a restore that turns into a redesign. The pull request does what the card asks; everything else becomes a proposed follow-up.
- **minimize-reader-load**: Apply when reviewing or shaping code that's hard to trace. Count layers between question and answer, and hidden state in the reader's head; collapse one-caller wrappers and shrink mutable scope.
- **model-the-domain**: Apply when writing stateful logic, or when code branches a lot or repeats a shape assumption across files.
- **never-block-on-the-human**: Apply when about to ask the human anything: whether to do X on reversible work, or a fact you could observe.
- **one-name-per-concept**: Apply when naming a field, parameter, event attribute, column or log key that carries something the system already names somewhere else. One concept keeps one name and one shape on every surface.
- **outcome-oriented-execution**: Apply during planned rewrites and migrations with explicit phase boundaries. Converge on the target architecture; don't preserve smooth intermediate states with throwaway compatibility code.
- **prove-it-works**: Apply after completing a task, before declaring done. Verify against the real artifact (run the feature, read the actual value, inspect the diff), not a proxy, self-report, or 'it compiles.'
- **record-before-side-effect**: Apply when code calls something outside the service that cannot be taken back (a payment, a signature, an order placed, a payout). Record first, derive the idempotency key, compare-and-set the status, bound the retry, treat an unconfirmed outcome as unknown.
- **redesign-from-first-principles**: Apply when integrating a new requirement into an existing design.
- **separate-before-serializing-shared-state**: Apply when concurrent actors might write to the same file, branch, key, or state object. Eliminate the sharing first; serialize structurally only when one shared writer is a real invariant.
- **sequence-verifiable-units**: Apply to multi-step work (sweeps, migrations, runs of similar edits) and to how you stack pull requests. Break work into small units that each end in a verifiable state, check each before the next, and order delivery so the sequence proves itself to a reviewer.
- **size-by-consequence**: Apply when deciding how much mechanism a risk deserves (a guard, a helper, a retry, a lock, a test). Size it by what happens when it fails and by what the rest of the code already accepts.
- **subtract-before-you-add**: Apply when sequencing an addition, refactor, or rewrite. Remove dead code, redundant validators, and stub references first, then build on the simpler base.
- **test-behavior-not-implementation**: Apply when writing, changing or keeping a test. Call the code the way its users do and assert the exact result they see; rewrite or delete a test that would still pass with the code wrong.
- **type-system-discipline**: Apply when designing types, reviewing a function signature, or writing code in any statically-typed language. Make illegal states unrepresentable, brand semantic primitives, parse external data at boundaries, refuse to lie to the compiler, exhaust variants, derive from authoritative schemas.
- **what-not-how**: Apply when handing work to an agent that holds the knowledge of how it is done, such as an engineer that reads the repo's rules: a brief, a fix request, a doubt about its diff. Say what is wanted, why and what proves it; the agent decides how.
