Every line that ships traces to evidence.

1. Reproduce it on the surface where it happens: locally; in a shared environment by
   reading its logs and data, never writing; in CI under the condition CI runs it. Ask the user only after driving
   every surface as far as it goes.
2. Find the cause by elimination, seeded with the **how** skill and `git log` and `git blame`, and
   confirm it with evidence.
3. Decide whether to run the **architect** skill per `../../references/architect-decision.md`.
4. Spawn an `geovane:engineer` with `task.md`, the cause with its evidence, and `sketch.md` to
   read, and the path of `rationale.md` to open only for a question the sketch leaves. Without a
   sketch, it reads the trail's `decision` notes instead.
   Its failing test reproduces the bug.
5. Prove the fix locally: the reproduction of step 1 now passes. When a caller or a partner saw
   the bug, spawn a `geovane:delegate` (sonnet, medium) with
   `../e2e-local.md` as its prompt, the worktree and the scenario. Run it even when the engineer's tests pass: they set up
   their own data and config, while this proof starts the service as it runs, drives it as its
   caller does and reads the outcome where it lives. A defect only in CI is proven
   by the pull request's CI.
6. When the trail has a `docs` line, write it with the **spec** skill.
7. Open the pull request with the **commit** skill.
8. Run the **PR babysit** playbook until the pull request is approved.

**Reply:** what was broken, its cause with its evidence, the fix, and the failing and the passing
output.
