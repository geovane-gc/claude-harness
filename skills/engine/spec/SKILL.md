---
name: spec
description: Writes a repo's docs/, the one place for what a repo's code cannot tell (how to run, call and operate the service, a business fact, a partner's behavior, the reason for a decision). Adds the facts a run found to the page that owns their topic, or rebuilds its pages so each fact has one home and nothing the code shows stays. Use for any write to a repo's docs/.
argument-hint: "<the facts or a file that holds them, or \"the whole docs\"> [the folder to write in]"
context: fork
background: false
model: sonnet
agent: geovane:delegate
---

Write into the repo's docs, in the folder the caller names, or the current directory when it names
none. `$ARGUMENTS` is either facts to add, or "the whole docs" to rebuild them. The caller owns the
branch, the commit and the pull request. This skill edits the docs and returns.

## What goes in

A fact goes in when reading the code cannot tell it. Examples are how to get a token, how to play a
partner's event and read the result, a partner's behavior, and why a choice was made. What the code
already shows stays out: field tables, status codes, class names, payload specs. So does what held
for one run only.

## Who owns what

Each fact has one home, in the page `templates/layout.md` gives it. Another page that needs it names
the home in one line.

Leave `README.md` as it is: it holds only what a feature never changes.

`CLAUDE.md` and `.claude/` are harness: they change through the harness-change playbook, never here.

## Adding facts

1. Read every page of `docs/`, starting with `docs/index.md`.
2. Put each fact in the page that owns its topic, next to the line it qualifies. Where a line says
   the opposite, fix that line instead of adding another. When no page fits, open one named
   for its topic and list it in `docs/index.md`.
3. Write only the facts given, and from a run's `trail.md` only its `docs` notes: a command goes in
   as the caller gave it, except that a value the code already holds is read from its file (see
   Writing).

## Rebuilding the whole docs

1. Read every page of `docs/`, and the code they describe on the default branch: the Makefile, the
   compose and config files, each module's entry point.
2. Check each statement against that code: run the command, read the line it names. One the code
   contradicts gets fixed or goes; one the code shows plainly goes.
3. Lay the pages out as `templates/layout.md` shows, move each statement that stays to its page, and
   delete the copies.

## Writing

Use the real names: the command, the file, the variable, the route. Give each thing one name.
Write commands in code blocks the reader can paste. When the code already holds a value (a request
body, an event's message, the id a stub answers, a port), name the file that holds it and never copy
the value: write the command so it reads the value from that file (`--message file://…`, `-d @…`).
Cut every word that does no work.

## Answer

Return the pages you changed, each fact with the page and section it went to, and each statement you
moved, cut or fixed, with the reason and its evidence (the code line, or the command and its output).
