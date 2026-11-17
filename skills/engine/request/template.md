# {Card title: the change, in a few words}

{Who} needs {what} so that {why}. One sentence that could turn out false.

## Acceptance criteria

The happy path, and each failure the business decided. A failure the repo's conventions already
decide stays out. Each scenario is testable as written and has a unique name.
Every scenario must start from a situation that really happens: one the system produces today,
or one this work produces. The Given must name that situation and what produces it. A scenario,
test or fixture built from a situation nothing produces is wrong and must be rewritten.

### {Scenario name}

Given {the situation}
When {the action or event}
Then {the outcome}

## Out of scope

- {What a reader would otherwise assume is included.}

## Decisions

- {A decision from the rounds that nothing written says}, because {why}.

## Depends on

- {Partner, team or other story this cannot ship without.}

---

# Task {n}: {what the task delivers, in a few words}

## Goal

{The card's need in one sentence.} {The part of it this task delivers.}

## Scope

- Repo: {the one repo this task changes}
- Waits for: {the tasks whose code this one cannot be written without; an order of deploy goes
  to Dependencies; delete the line when nothing}
- Out of scope: {what a reader would otherwise assume is included}

## Contracts

For each entry point the task creates or changes (endpoint, consumer):
- In: {path and body, or the event and its payload}
- Out: {each answer the happy path and the decided failures get}
A change to an existing contract shows what it was and what it becomes.

## Scenarios

The happy path of this slice, and each failure the card decided or a partner's contract imposes.
Every scenario must start from a situation that really happens: one the system produces today,
or one this work produces. The Given must name that situation and what produces it. A scenario,
test or fixture built from a situation nothing produces is wrong and must be rewritten.

### {Scenario name}

Given {the situation and what produces it}
When {the action or event}
Then {the outcome}

## References

- {The library, SDK, partner's doc or public API doc the task builds on, by name or URL}: {what it
  gives the task}.

The task says what it delivers. It may point at a file or a line as evidence of where the problem is;
it never says how to change it, or points at another service's code to copy.

## Dependencies

- {Team, infra, secret or config that must exist.}

## Assumptions

- {What is taken as true without proof.} Confirm {with whom or how}.

Delete any section that would be empty, except Goal, Scope and Scenarios.
