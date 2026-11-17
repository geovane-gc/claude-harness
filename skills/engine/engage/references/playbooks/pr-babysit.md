You babysit the pull request yourself. It is merged only on the user's word, in the request or in a
later message; that word holds for the rest of the run, so never ask for it again. Never read the pull request's state
(`gh pr view`, `gh pr checks`): the watcher's verdict is that state, and the evidence a note cites.

The scripts are in `../../scripts/`.

1. Find the pull request's worktree with `git -C <repo> worktree list`. None: fetch and add one on
   its branch with `git -C <repo> worktree add`.
2. Run `watch-pr.sh <pr url>` with Bash `run_in_background` and end your turn. Its verdict wakes you
   with the path of the file that holds it. After you act on a verdict, run the script again with
   the same arguments, unless the step says stop.
3. `COMMENTS`: step 5, with each item and the file that holds its text.
   `CONFLICT`: run `merge-base-in.sh <pr url> <worktree>`. The first word of its answer:
   - `SAME_TREE` or `MERGED`: push the worktree with the **commit** skill, passing it the worktree
     and the pull request's URL.
   - `CONFLICTS`: step 5, with the files it lists, to solve by merging the base in, never with a
     force push.
4. `CI_FAILED`: decide where each failure lies from its `errors` and the verdict's `changed_files`.
   Read its log only when the errors do not tell. A check whose details sit behind a login, such
   as a security scan's page: open it with the browser tools in the user's Chrome, which is logged
   in. Never ask the user to open or paste a page, and never look for credentials.
   - In the change: step 5, with the check, its errors and its log.
   - Flaky (a runner, the network, a timeout): rerun its failed jobs once with
     `gh run rerun <run> --failed`. The same failure again is not flaky: decide again.
   - In the base (code, a dependency or a tool the change does not touch): look for a pull request
     that fixes it, open or merged, in any repo, with `gh pr list --state all --search`. None: run
     the **Bug fix** playbook for the failure, in the repo the fix belongs to. With the fix found or
     opened, name both links in your reply, and run `watch-pr.sh <pr url> --fixed-by <the fix's url>`
     in place of step 2's call.
     A dependency CVE from a scanner: brief the engineer to bump the library that brings it in
     to a release that fixes it first, and to pin a transitive version only when no such release
     exists.
5. Spawn a new `geovane:engineer` with the worktree, the pull request's URL and what to fix. Brief it to
   commit with the **commit** skill, passing it the worktree and the pull request's URL, and to
   reply to each item by writing the reply to a new file outside the worktree and posting that
   file:
   - fixed: "Fixed in <sha>: <what changed>"; not real: the file:line or the test that shows it;
   - a thread: `reply.sh <pr url> <comment> <file>`, then `resolve.sh <thread>` when fixed;
   - a comment, a review or a check: `gh pr comment <pr url> --body-file <file>`;
   - after disputing a Claude Code Review thread: `request-review.sh <pr url>`. When it prints
     `limit`, the pull request already has two `@claude review` comments: ask for no other review;
   - an item that needs a decision about money, security, data or a migration: no reply.

   Name in your reply each item the engineer left for a decision, with what it found.
6. `APPROVED`: when the user said to merge, run `../../../../tools/commit/scripts/merge.sh <pr url>`:
   it merges, or says what stops it. Send the user a Slack direct message (to their own user id, which the Slack send tool names) with
   the link, who approved it, the checks count, each open thread (its link, who opened it, its first
   line), each warning (its check, its conclusion or annotations, its link), and merge.sh's answer.
   A warning with an annotation on a file in `changed_files`: step 5 for it, without waiting for the
   engineer.
   Stop. Only this verdict says the pull request is approved.
7. `FIX_CLOSED`: send the user a Slack direct message with both links: the fix was closed without
   being merged, and this pull request still fails. Stop.
8. `FIX_FAILED` or `RELEASE_FAILED`: send the user a Slack direct message with the pull request's
   link and each failed run's link. Stop.
9. `MERGED` or `CLOSED`: stop.

**Reply:** the link and its final verdict, what each round fixed and disputed, and the Slack
messages.
