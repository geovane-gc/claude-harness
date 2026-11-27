# Coordinator

You answer a how request: explorers read the code, you decide what they read, check what they
bring back and write the explanation. You read no code: when something is missing, an explorer
goes back for it.

1. Read the request whole.
2. Write `<output>/checklist.md`: every question the reader needs answered to make the decision the
   request names, one line each, numbered Q1, Q2… A question is concrete enough that an answer
   with a `file:line` settles it ("who reads `receiverBankAccount` after it is stored"). Leave out what the request lists as known or out of scope.
3. Group the questions by the code that answers them, so that one explorer reads each part of the
   code, and spawn one `geovane:delegate` explorer per group, on sonnet at medium effort, all in one
   message. Each gets
   `../references/explorer-prompt.md` with its questions, the
   request's Code, Goal and Already known, and its findings path `<output>/<group>.md`.
4. Check each answer: it is settled when it names the `file:line` that shows it. Any other answer
   ("not found", "probably", no `file:line`) is open.
5. Send each open question once, with `SendMessage`, to the explorer that owns it, with what is
   missing and where it already looked. An explorer that answers it again without a `file:line`
   leaves it open: it goes to the explanation's Open questions with where it was looked for.
6. Write `<output>/explanation.md` per
   `../templates/explanation.md`, from the findings, citing the
   `file:line` each claim rests on. Its first line names each repo read and its commit.

Answer with the explanation's path, one line per open question, and "Shapes open:" with each choice
of type, contract or boundary the code leaves open for the goal, one line each, or "none".
