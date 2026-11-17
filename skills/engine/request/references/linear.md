# Linear

Call Linear through the Linear MCP.

## Publish the card

`save_issue` with `title` = the card's title line without its `# `; `description` = the card's body
below the title line, verbatim; the `team`, `project` and `labels` of step 5; `state` =
Backlog, or Triage when step 5 was skipped; no assignee. When the request came as a Linear issue, update that issue instead of creating
one.

## Publish a task

Publish the tasks in order, each with `save_issue`:

- `title` = the task's title line without its `# Task {n}: ` prefix. `Task {n}` only numbers the
  tasks inside `request.md`, before Linear gives them identifiers.
- `description` = the task body below the title line, verbatim, with each `Task {n}` in "Waits for"
  replaced by the identifier Linear gave that task.
- `parentId` = the card; `team` and `project` = the card's; `labels` = the task's repo from the
  `Repository` group.
- `state` = the card's; no assignee.
- `blockedBy` = the identifiers of the tasks it waits for. A task that waits for something is never
  published without its `blockedBy`.

## Check the tasks

`get_issue` each task with `includeRelations` true. Its `blockedBy` must hold exactly the
identifiers in its "Waits for"; when it does not, `save_issue` the missing ones and check again.
