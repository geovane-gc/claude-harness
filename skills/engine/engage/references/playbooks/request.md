1. Write the handoff to `<run folder>/request-<slug>.md`, `<slug>` naming it in a few words:
   - what needs doing, as the customer or support would see it;
   - each fact you have, with its evidence (a `file:line` at a commit, a command and its output, a
     Linear id) and whether you measured or inferred it;
   - what you did not check, and how to check it;
   - the repo and its commit, the task it came from, and the cards it touches;
   - why it is outside the task.
2. Spawn an `geovane:atlas-agent` on sonnet at high effort, in the background, with: "Run the **request**
   skill for work the caller found outside its task. Read `<handoff path>` whole: its facts count
   as read; run step 1 for everything it lists as not checked. Answer with the ids of the cards you
   created."
3. When it answers, settle its `problem` note in the trail with the card ids.

**Reply:** none of its own; the run's reply names each card.
