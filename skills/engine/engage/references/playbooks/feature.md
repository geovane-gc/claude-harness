1. Learn the part the change touches with the **how** skill.
2. Decide whether to run the **architect** skill per `../../references/architect-decision.md`.
3. Spawn an `geovane:engineer` with `task.md` and `sketch.md` to read, and the paths of
   `explanation.md` and `rationale.md` to open only for a question the sketch leaves. Without a
   sketch, it reads `task.md`, `explanation.md` and the trail's `decision` notes.
4. Prove it end to end on the engineer's worktree: spawn a `geovane:delegate` (sonnet, medium) with
   `../e2e-local.md` as its prompt, the worktree and the scenario. Run it even when
   the engineer's tests pass: they set up their own data and config, while this proof starts the
   service as it runs, drives it as its caller does and reads the outcome where it lives, such as
   the stored record or the published event.
5. When the trail has a `docs` line, write it with the **spec** skill.
6. Open the pull request with the **commit** skill.
7. Run the **PR babysit** playbook until the pull request is approved.

**Reply:** each pull request link, what changed and for whom, how it was proved and what stays
unproven, the decisions left open.
