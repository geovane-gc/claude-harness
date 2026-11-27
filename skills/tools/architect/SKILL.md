---
name: architect
description: "Sketch types, signatures, and module structure before code, then stay in the loop while implementation fills in. Use for /architect, 'architect this', 'design this', or non-trivial work where jumping to code would lock in the wrong shape."
---

# Architect

Sketch types, function signatures, class shapes, and module boundaries with `not implemented` bodies and pseudocode. One runner designs it, weighing at least two shapes, then code fills in against its sketch.

## Start

Open a todolist with one entry per phase before starting.

1. Ground
2. Sketch
3. Agree
4. Implement
5. Scrap

## Phase A: Ground the problem

Build a real mental model of every system the new code touches. Use the how explanation your caller names, and run the **how** skill only over a subsystem it does not cover. Naming a file isn't grounding. Produce the architectural explanation `how` prescribes.

Skip Phase A only when the work is genuinely greenfield with no surrounding system to integrate.

## Phase B: Sketch

Spawn one `geovane:delegate` runner on opus at high effort, with `references/runner-prompt.md` as its prompt, the design-sketch task (the goal and its constraints, never a candidate shape: a runner handed one judges it instead of designing), the Phase A grounding artifacts and the folder to write in. The run folder is the one the caller names, or `${user_config.workspace}/.runs/architect-<slug>/` when it names none, `<slug>` naming the design in a few words. The runner writes `<run folder>/architect/sketch.md` and `<run folder>/architect/rationale.md`.

Read the sketch end to end and screen it against [`references/design-red-flags.md`](references/design-red-flags.md). Assume the next contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Prefer the design where a change that looks right from one file is right for the whole repo.

Where the sketch trips a red flag, or a shape in its Alternatives considered is one a future maintainer can extend more easily without breaking invariants, change the sketch. Record each change in the rationale's "Review" section, or "none".

## Phase C: Agree (opt-in)

Default: proceed directly to implementation with the sketch. No human checkpoint.

Opt in to a checkpoint when the invoker explicitly asks: "/architect with checkpoint," "stop and show me before implementing," or similar. Then surface the sketch and pause for sign-off.

The reviewed sketch can ship as its own commit either way, as the "scaffold first" mode of the **foundational-thinking** principle skill. Planned and scoped breakage during fill-in is fine.

If the human pushes back on the shape (in a checkpoint or after the fact), treat that as Phase A evidence. Re-ground and re-run Phase B before writing more code.

## Phase D: Implement against the sketch

When a playbook or an agent runs this skill as one of its steps, the skill returns after the
review, and the caller's Implement step does this phase with the sketch as its brief.

Replace `not implemented` bodies with code, pseudocode with logic. The reviewed sketch is the contract. Deviations from it are signal to surface, not friction to absorb silently. If a function needs a parameter the sketch didn't anticipate, ask whether the sketch was wrong, the requirement was missed, or the implementation is overreaching.

## Phase E: Scrap when the architecture is wrong

If implementation keeps producing friction the sketch can't absorb, throw the sketch out. Don't bolt fixes onto a wrong design, per the **redesign-from-first-principles** and **fix-root-causes** principle skills.

The signal is a *pattern*, not single instances. Tells:

- The same shape of workaround appearing repeatedly across unrelated code.
- Multiple unrelated edge cases that all need special-case branches.
- Types that need escape hatches (`any`, casts, optional fields always set in practice) to compile.
- The "we need a lock" reflex when the sketch said the state wasn't shared.
- Callers having to know the abstraction's internal rules to use it.
- Two or more independent Phase D deviations of the same shape across the implementation.

Use judgment. A few edge cases don't condemn an architecture. Some problems are legitimately complex. Complexity in the data is not complexity in the design.

When you scrap:

1. Re-run the **how** skill over what's been built.
2. Redesign as if the new constraints had been day-one assumptions, per redesign-from-first-principles.
3. Subtract before adding, per the **subtract-before-you-add** principle skill. The new sketch should be smaller than the old one before it grows.
4. Return to Phase B and run it again.

## Outputs

One file with new types and signatures for small changes. Module map plus type definitions for larger work. The rationale ships alongside, shaped per `templates/rationale.md`, including the usage sketch and the review. Answer with the paths of both files.
