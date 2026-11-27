---
name: commit
description: Commits the current change, pushes it and opens a pull request, picking the branch from the repo's state.
when_to_use: Any commit, push or pull request, asked for or not.
argument-hint: "<worktree> [the task folder] [the task id] [a pull request that goes first] [the pull request whose review or checks asked for the change]"
context: fork
background: false
model: sonnet
agent: geovane:delegate
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/state.sh *), Bash(${CLAUDE_SKILL_DIR}/scripts/check-title.sh *), Bash(${CLAUDE_SKILL_DIR}/scripts/ship.sh *), Bash(${CLAUDE_SKILL_DIR}/scripts/open-pr.sh *), Bash(${CLAUDE_SKILL_DIR}/scripts/edit-body.sh *)
---

# Commit

## Guidelines

- Every call ends with each thing of the change pushed and in an open pull request.
- One commit per thing: commit all of it at once; pull requests are squash-merged.
- A change asked for by a pull request's review or failing checks goes in that pull request: when the arguments name the pull request that asked for it, stay on its branch.
- A pull request delivers one thing: what becomes possible for whoever is outside the code it changes.
- Its title says that thing in one sentence, without "and".
- It ships alone: merged and deployed by itself, nothing breaks, and it carries what that takes (tests, migration, docs).
- A new concept and its use are two things when each can ship alone.
- Prefer five narrow pull requests to one large one.
- A change that holds more than one thing ships as one pull request each. A file that holds both goes with the first, and that pull request's Scope says so.
- Dependent work stacks. A change that builds on another open pull request branches from that pull request's branch and opens against it; independent work branches from the default branch. Update a child by merging its parent in.

## Steps

The worktree is the one the arguments name: every script but check-title.sh takes it first, and every git command you
run yourself is `git -C <worktree>`. When the arguments name no worktree, answer
`BLOCKED: name the worktree to commit` and do nothing else: the current folder may hold another
session's work. The pull request's description comes from the task
folder, when the arguments name one: `task.md` holds what was asked, the `decision` notes of
`trail.md` the design choices, its `fact` notes the Verification. Without a task folder, it comes
from the diff.

1. Read the state: `${CLAUDE_SKILL_DIR}/scripts/state.sh <worktree>`.
2. Write the title, in at most 60 characters:
   - Type: pick from `references/types.md`.
   - Scope: the area the change touches, in one word: the module or the capability.
   - Description: imperative, naming a real symbol when one carries the change.
   - Task: when the arguments name a task id, end the title with it in parentheses, as
     `fix(policy): verify the signature before auto-approval (ENG-450)`. It does not count
     toward the 60 characters.
   - Run `${CLAUDE_SKILL_DIR}/scripts/check-title.sh "<title>"` and rewrite until it prints `ok`.
3. Pick the branch:

   | branch  | pr                  | then       |
   |---------|---------------------|------------|
   | default | —                   | new branch |
   | other   | none                | stay       |
   | other   | open, same thing    | stay       |
   | other   | open, another thing | new branch |
   | other   | merged or closed    | new branch |

   Another thing: the open pull request's title would need "and" to cover this change too. New branch: `git -C <worktree> fetch origin`, then `git -C <worktree> switch -c {type}/{slug} origin/{base}`, `{base}` being the `base` that state.sh prints, the slug being the title's description in kebab-case, prefixed by the task id in lowercase when the arguments name one (`fix/eng-450-verify-signature`). The branch never names the repo.
4. Commit and push: `${CLAUDE_SKILL_DIR}/scripts/ship.sh <worktree> "<title>" [the paths of this thing, when the change holds more than one]`.
5. The description follows the `template` that state.sh prints. The skill's own, `templates/pr.md`: keep `Closes {TASK_ID}` only when the arguments name a task id, list each pull request that goes first under Depends on, marked with what this one waits for, not with its state today, and drop a section with nothing to say. A repo's template: fill every section, checkboxes reflecting reality, then add the Spec, Review, Verification, Assumptions and Depends on sections of `templates/pr.md` after it.
   - Unless you stayed on a branch whose pull request is open, open one: run `${CLAUDE_SKILL_DIR}/scripts/open-pr.sh <worktree> {base} "<title>"` with the body on stdin.
   - When you stayed on a branch whose pull request is open, and the description no longer matches the change, pipe the whole new description to `${CLAUDE_SKILL_DIR}/scripts/edit-body.sh <worktree> <url>`.
6. When the change holds another thing, go back to step 2 for it; its files come along to the new branch.
7. Answer with the URL of each pull request, `opened` before each one this call opened.
