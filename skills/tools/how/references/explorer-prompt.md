# Explorer

Build each explorer's prompt from this template. Fill in the placeholders.

---

You read code to answer the questions below; the one file you write is your findings file. Other
explorers answer other questions about the same goal, so read only what your questions need.

## Goal

{GOAL}

## Code

{CODE}

## Already known

{ALREADY_KNOWN}

## Your questions

{QUESTIONS}

## Findings

Write to {FINDINGS_PATH}, one section per question, headed by its number:
- the answer, with the `file:line` of each line that shows it;
- or "not found", with where you looked.

Add at the end anything you found that a question did not ask but the goal needs, with its
`file:line`. Answer with the findings path.
