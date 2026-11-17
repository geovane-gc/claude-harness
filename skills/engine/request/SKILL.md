---
name: request
description: >-
  Turns a request for a change in one of your services into a Linear story card
  with its tasks as sub-issues, ready for /engage. Reads everything that
  already answers a question, asks the remaining decisions in rounds with a
  recommended answer each, and keeps the story to the happy path plus the
  failures the business decides. Called as a playbook step, it asks no one and
  takes its recommended answers.
argument-hint: "<the request, in a few words, or a Linear issue id>"
---

The request is `$ARGUMENTS`: a sentence, or the id of a Linear issue that holds it. Work in a run
folder, `${user_config.workspace}/.runs/request-<slug>/`, where `<slug>` names the request in a few words.
When that folder already has a `notes.md`, this is a resumed request: read it and go on from where
it stopped.

When you invoke this skill yourself (a playbook step, a loop) and the user did not type
`/request`, ask no one, even with the user in the conversation:

- each round of step 2 takes its recommended answers as the decisions, written in `## Decisions`
  as "taken by the agent";
- step 4 is skipped for work the caller found outside its task; otherwise it judges once: fix each finding of a FAIL and go on; an UNKNOWN publishes nothing and
  returns the judge's answer;
- step 5 is skipped.

## 1. Read before asking

A question someone could answer by reading is a wasted question. Before the first round, read:

- the repo the request changes (the current directory, unless the request names another one under
  `${user_config.workspace}/`): its code, `README.md`, `docs/` and `.claude/`;
- the repo's `CLAUDE.md`, `REVIEW.md` and `.claude/rules/`: what the repo's conventions already
  decide;
- the services that call this one or that it calls, and the contracts between them;
- the partner's SDK and docs, when the request depends on a partner;
- the API docs, when the request touches a public API;
- the Linear issue of the request, when there is one, and the issues it links to.

Write each fact you find in `notes.md`, under `## Facts`, with its source (a path, a URL, an issue
id). Facts are never asked. A fact only someone else knows becomes an Assumption with how to confirm
it.

## 2. Ask the decisions, in rounds

What is left after reading are decisions: what the business wants where nothing written says it.
Ask them in rounds. A round holds every decision whose prerequisites are settled, numbered, each
with your recommended answer and why in one line, worded so that "sim" accepts it. The user answers
only the numbers they disagree with. A decision that depends on another waits for the next round.

```
1 A new account starts ACTIVE or PENDING?
  → PENDING: the partner approves it later
    (partner docs, account onboarding)
```

Ask only about the happy path. These are never questions, because the repo's conventions already
decide them and the code does it on its own: something that already exists, something that does not
exist, a change the current state does not allow, the same message twice.

The first round also carries two questions, with your recommendation from what you read:

- Is there data in production that the change touches (records without a new field, old formats)?
- Is there something similar already built, in any repo?

The last round ends with one question: "Is there a failure where the business decides something,
such as reversing, notifying or trying again?" Each yes becomes a scenario.

Write each answer in `notes.md`, under `## Decisions`, in the user's words. When the user cannot
answer and someone else can, write the question under `## Open` with who answers it, and stop: the
next `/request <slug>` takes the answer the user brings and goes on.

## 3. Write the card and the tasks

Write `request.md` in the run folder with [template.md](template.md): the story card first, then its
tasks.

Slice the tasks:

- data two or more tasks need (a field to read, store or send) is a task of its own,
  first, and they wait for it;
- each task is a vertical slice: it changes one repo, fits one pull request, ships alone and leaves
  the system working;
- each task fits one agent session: a coding agent can finish it without its context running out;
- a task waits for another only when its code cannot be written without the other's code, as
  in the same repo building on it; tasks in different repos that meet at a contract the card
  states run in parallel, and the order in which they deploy goes into Dependencies;
- a request that fits one pull request is one task.

Work that belongs to another team goes into the Dependencies of the task that needs it.

## 4. Judge

Spawn the `geovane:judge` agent with the absolute path of `request.md`, then the absolute path of
[rubric.md](rubric.md).

- PASS: go to step 5.
- FAIL: a missing fact goes back to step 1, a missing decision to a round of step 2, anything else
  means rewriting. Judge once more. After a second FAIL, show the findings to the user and let them
  decide.
- UNKNOWN: show the judge's answer as it came and wait for the user.

## 5. Review

Show the user, in one message: the card's statement and scenario names, one line per task (title,
repo, what it delivers, what it waits for), the Assumptions, and the Linear `team`, `project`
and `labels` it will use: the team and project of the latest issues of this repo in Linear, and,
when the card changes one repo, that repo from the `Repository` group. End with two options in plain text: publish now, or adjust. "Adjust": take the
change, rewrite, judge again, show again.

## 6. Publish

Publish the card, then its tasks, then check them, as [references/linear.md](references/linear.md)
says.

Answer with one line per issue: its identifier, URL and the identifiers it is blocked by. Keep the run folder: it records the facts
and the decisions behind the card.
