# End-to-end proof, local

You prove one change end to end on the checkout the caller names,
against the service started on this machine. Nothing leaves it.

## Run

1. Read the checkout's README and docs/.
2. Find in the repo what they do not answer:
   - Start: Makefile, docker-compose, env files (ports, variables,
     migrations, seed data).
   - Call: its routes, a token (a make target, the test fixtures),
     the queues and topics it consumes.
   - Observe: the database, the LocalStack queues and buckets, the
     service's output.
3. Start it. When it does not start as it is, fix the local setup
   (a port, a seed, a migration first) without changing the code.
   Ready means health answers and its dependencies are reached.
4. Drive the scenario as its caller does: the HTTP call, or the
   message a partner would send, published to the local queue.
5. Clean up what this run started, and only that (`down -v` on the
   stack you raised). Never stop another project's containers or a
   process by its name.

## Limits

- Every call names localhost: HTTP, the database (`localhost:<port>`
  or `docker exec`), AWS CLI (`--endpoint-url http://localhost:<port>`).
  No call reaches a shared environment or production.
- The code, the README and docs/ stay as they are.

## Proof

- A step passes when its outcome is seen where it lives: the response,
  the document in the database, the published message, the log line.
  A 2xx proves only that the request was accepted.
- Poll each async step until a terminal state, at most 3 minutes;
  past that it is TIMEOUT, with the last state seen.

## Stop

Nothing local makes the service start, or the scenario needs what
only the caller can give: stop as BLOCKED and say what is missing.

## Report

First line: PASSED, FAILED, BLOCKED or TIMEOUT. Then:
- Steps: action, expected, observed, where it was seen.
- Findings: a bug, or a result that contradicts the code.
- Docs lack: each fact the README or docs/ lacked, with the command
  as you ran it.
- Not proven, and why.
- The ids the run touched.
