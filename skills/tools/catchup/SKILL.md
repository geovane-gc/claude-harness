---
name: catchup
description: >-
  Catches the user up on the work in this conversation: where it
  stands now, what changed since their last message, the next step
  suggested, and the decisions waiting on them, one at a time.
disable-model-invocation: true
---
Change nothing. Agent results are not the user's messages.

1. Check the state of every agent, PR, branch and run this
   conversation touched: done, still running, or not checked.
2. List the open decisions only the user can make (not work you
   can do), including ones raised before their last message.
3. Write these three parts, in this order, calling every thing by
   the name the user knows:
   - Where it stands: the goal of the work in one line, then each
     part of it marked ✅ done, 🟨 in progress or ⬜ not started.
   - Since their last message: what happened, most important
     first, each with what it changes for them, or that nothing
     did.
   - Suggestion: the next step you recommend, and why, in one line.
4. Then the first decision, with its count, such as 1 of 2: the
   options with their cost, and the real case it decides, as it is
   now and as you suggest it, with what stays as it is without an
   answer. The next one waits for the answer.
