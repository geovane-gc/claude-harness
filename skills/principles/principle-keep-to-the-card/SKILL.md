---
name: principle-keep-to-the-card
description: "Apply when the change grows past what the card asked: an extra hardening, a new binding, a side behavior change, a review finding that widens the scope, or a restore that turns into a redesign. The pull request does what the card asks; everything else becomes a proposed follow-up."
disable-model-invocation: true
---

# Keep to the Card

A pull request is reviewed against the card it closes. Everything it does beyond the card is
unreviewed risk, and it hides the change the card asked for.

- **The card is the scope.** Before each file the change adds, name the line of the card it serves.
  A file with no line goes out.
- **Findings are not orders.** A real finding outside the card's lines becomes a follow-up card,
  not a commit. Inside the card's lines, or Important by the repo's `REVIEW.md`, it is fixed here.
- **A restore is a revert.** "Bring back X" restores X as it was. A better X is another card.
- **Propose, do not fold.** Extra hardening goes in the reply as a proposal with its reason and
  cost, for the user to turn into a card.
- **Size by the diff.** A diff far larger than the card's ask is a signal to stop and ask, not to
  push on.
