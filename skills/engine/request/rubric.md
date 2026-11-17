# Rubric: request card and tasks
Reader: a team of coding agents that reads only this card and one of its tasks, the repo's rules
and the references the task points to, and must model and
implement the change without asking anyone.

## Check: happy path
Question: Does the card state one change and cover its happy path end to end?
Pass when: the card's first sentence names who needs the change and what changes, and could turn out
false; every step of the happy path, from what starts it to its outcome, has a scenario; every scenario of the card is covered by a scenario of at
least one task.
Evidence: the missing step, or the card scenario no task covers.

## Check: only decided failures
Question: Are the failures in the card and tasks only those someone decided or a contract imposes?
Pass when: each failure scenario traces to a decision in the card or to a partner's or another
service's contract. A scenario for what the repo's conventions already decide (something that
already exists, something that does not exist, a change the current state does not allow, the same
message twice) is a finding.
Evidence: the scenario, and the convention that already decides it.

## Check: stands alone
Question: Can the Reader start a task without asking anyone anything?
Pass when: every fact the Reader needs from outside the repo (decisions, contracts of partners and
other services, existing production data, dependencies) is in the task or in a reference the task
points to and the Reader can open. A fact written as an Assumption, with how to confirm it, counts
as given.
Evidence: the missing fact, and the scenario or section that needs it.

## Check: free of how
Question: Does each task leave every design decision to the Reader?
Pass when: the task states what it delivers and the contracts that already exist, and leaves classes, files, layers, internal names and patterns to the
Reader. Describing what already exists counts as context, including a file or a line that shows where the
problem is; another service's code to copy is a finding.
Evidence: the sentence that makes a design decision the rules and the code let the Reader make.

## Check: scenarios
Question: Can each scenario become a test as written, from a situation that really happens?
Pass when: each scenario has a Given, a When and a Then; every scenario name is unique.
Every scenario must start from a situation that really happens: one the system produces today,
or one this work produces. The Given must name that situation and what produces it. A scenario,
test or fixture built from a situation nothing produces is wrong and must be rewritten.
Evidence: the scenario, and what cannot be tested or what nothing produces.

## Check: contracts
Question: Does each task give the contract of each entry point it creates or changes?
Pass when: each entry point has what enters and the answer of every scenario that reaches it.
Answers for failures the conventions decide are left to the repo's rules.
Evidence: the entry point, and the scenario left without an answer.

## Check: slices
Question: Can each task ship alone, in order?
Pass when: each task changes one repo, fits one pull request and leaves the system working when
merged; each task names the
tasks it waits for, and none waits for a task that comes after it.
Evidence: the task, and what it cannot ship without.
