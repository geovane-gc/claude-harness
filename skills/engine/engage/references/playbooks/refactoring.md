The structure changes and the behavior does not. A bug or a missing feature found on the way ships after this change,
never inside it: it would break the pin. A redesign that changes behavior is a Feature.

1. Learn the contract of the part involved with the **how** skill.
2. Decide whether to run the **architect** skill per `../../references/architect-decision.md`.
3. Spawn an `geovane:engineer` with `task.md` and `sketch.md` to read, and the paths of
   `explanation.md` and `rationale.md` to open only for a question the sketch leaves. Without a
   sketch, it reads `task.md`, `explanation.md` and the trail's `decision` notes. Ask it to pin
   today's behavior with tests that pass before any move, delete before it adds, move every caller of a
   changed interface in the same change with no shim, and check each rename in strings, docs and
   config.
4. Prove that the behavior did not change, on the service running locally: spawn a `geovane:delegate` (sonnet, medium) with
   `../e2e-local.md` as its prompt, the worktree and the scenario.
5. Keep it only when the code got easier to read; otherwise revert it and stop.
6. When the trail has a `docs` line, write it with the **spec** skill.
7. Open the pull request with the **commit** skill.
8. Run the **PR babysit** playbook until the pull request is approved.

**Reply:** the structure that changed, the pin it held against, the proof that behavior did not
change, what shipped and what was reverted.
