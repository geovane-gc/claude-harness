The request is the user's word to merge and to deploy to the environments it names: never ask for
it again. A merge of an infrastructure or deploy-config pull request applies it: read the plan its
CI posted first. Production needs the user's word for it, as the engage skill's Autonomy says;
without it, show the exact command and wait.

The scripts are in `../../scripts/` and `../../../../tools/commit/scripts/`.

1. List the pull requests: the ones the request names, or
   `gh search prs --author @me --state open --json url,title`.
   Run `watch-pr.sh <pr url> --max-wait 60` on each: its verdict is that pull request's state.
2. Order them: each one after what its `## Depends on` names (`deps.sh`), and the one that tells
   people about a change after the one that ships it. A stack counts as one, its bottom pull
   request, the one on the default branch: `merge.sh` on it folds the others into it first. Trail
   the order as a `decision`.
3. In that order: `APPROVED` → `merge.sh <pr url>`; lacking only an approval, when the user said to
   merge without one → `merge.sh <pr url> --without-approval`. Then `watch-pr.sh <pr url>` until
   `MERGED` or `RELEASE_FAILED`. `COMMENTS`, `CONFLICT` or `CI_FAILED` → the **PR babysit** playbook for that
   pull request.
4. Pull requests that only lack an approval, with every check their base requires green and no word
   from the user to merge without one: list them in the reply, in merge order.
5. Deploy what the request names, a service after the ones it calls, the way the repo deploys (its
   `CLAUDE.md`, README or deploy workflow). Production only as the engage skill's Autonomy allows;
   otherwise show the exact command.
6. Confirm the version running in each environment you deployed to, by reading it, never writing.

**Reply:** each pull request with its final verdict, what was deployed where with the run links,
and what waits on whom.
