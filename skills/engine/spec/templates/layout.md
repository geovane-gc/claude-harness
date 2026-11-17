# Layout of docs/

Every page is for whoever runs or changes that part of the service. Leave out a section with nothing to
say, and keep the others in this order.

- `index.md`: the list of pages, one line each saying what the page holds, nothing else.
- `how-it-works.md`: `## What it talks to`, a mermaid flowchart (solid arrows HTTP, dashed ones events)
  and a `| Dependency | How | When it fails |` table; `## The flow`, numbered steps, each linking the
  page that holds its reasons.
- `flows.md`: one `## {task}` per thing a person does by hand on the local stack, named by the task
  ("Get a token", "Create a withdrawal and read it back", "Reprocess a failed message"): the commands in
  order and what the reader should see. Starting the stack stays in the README.
- `operating.md`: opens with the runtimes, health, logs and traces, the pipeline and the
  infrastructure, then `## Dependency lockfiles`.
- `{aggregate}.md` and `{partner}.md`, one per aggregate and one per partner, opening with "The reasons
  behind {it}. The flow is in [How it works](how-it-works.md)."
- `messaging.md`: `## Our events`, `## What we consume`, `## Failures and the archive`.
- `indexes.md`: `## One catalogue per collection`, then `## The {collection} collection` for each one.
- `configuration.md`: opens with the environment variables and the infrastructure files, then `## Adding a queue`,
  `## Gateways`.
- `testing.md`: `## Containers`, `## Configuration`, then a section
  for anything else of the test stack that needs a reason.
- `mkdocs.yml` at the repository root, with no `nav`: `index.md` is the list.

Another service is named only when this one depends on it to run; whoever calls it is "the caller".
