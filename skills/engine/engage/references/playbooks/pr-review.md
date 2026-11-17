Nothing is pushed or merged unless the user asks. Claude Code Review already reads every
pull request on GitHub for bugs: this review looks at what it cannot see.

1. Run step 1 of the **PR babysit** playbook, then check the worktree's HEAD against the pull
   request's head commit. When they differ, fetch and check that commit out in the worktree.
2. Spawn a `geovane:atlas-agent` on opus at high effort with the worktree, the pull
   request's URL, the task it names and the reviews already on it. Brief it to weigh each
   finding by the repo's `REVIEW.md` (when the repo has none: 🔴 Important, 🟡 Nit,
   🟣 Pre-existing), and to review through these lenses, after the ones the request names:
   - Side effects: every amount, recipient and external side effect the diff touches, each with
     the retry, redelivery or crash that would break it.
   - Pattern: every class, function and test the diff adds or changes, none skipped, against
     the conventions of its component and against its sibling in the repo: the nearest code of
     the same kind, often beside it in the same file. A finding names the convention's heading
     or the sibling's file:line.
   - Outside the repo: each contract, stored shape and deploy order the diff changes. It
     settles who calls each contract, what is stored and what deploys first with a check it can
     run, such as a code search on GitHub, and returns what it cannot check as an open question.
   - The task: what the diff does against what its task asked, and what it does beyond it.
     What it does beyond the card is a finding (`principle-keep-to-the-card`).
   - Companions: whether an infrastructure, deploy config or library change must ship first.

   It leaves out what a review already on the pull request says. It returns the pieces it
   compared, each with its sibling, and each finding with the path and the line of the diff it
   belongs to, the comment as it would be posted, and the check that proves it.
3. Run each finding's check yourself, at the layer the claim names: a call is proven by a call
   site, and a fact about another repo by that repo's default branch on GitHub.
4. Where a finding disagrees with a review already on the pull request, name both with the
   evidence.

**Reply:** who the pull request is for and what it changes for them; each finding with its check,
the ones that would break something first; what stays unverified.

After the reply, write the review to a file as `post-review.py` reads it and run
`../../scripts/post-review.py <pr url> <file>` only in these cases:
- Someone else's pull request, with no finding left after step 3 and no open question:
  `APPROVE`, without asking.
- Any other case: on the user's word. It is a comment unless the user asked to request changes
  or to approve.

A finding the user wants fixed in a pull request of their own goes through step 5 of the **PR
babysit** playbook.
