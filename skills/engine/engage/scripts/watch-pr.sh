#!/usr/bin/env bash
# Watches a pull request until there is something to act on, then prints one verdict as JSON:
#   COMMENTS   threads and comments nobody answered yet, each with its ids and the file holding its text;
#              and each required check that warns (it ended neutral, or passed with a title that says it
#              failed) and has warning or failure annotations or that title: its name, url and annotations
#   CONFLICT   the branch conflicts with its base
#   CI_FAILED  a required check failed on the head commit and no check is still running; carries the
#              files the pull request changes (changed_files)
#   APPROVED   approved, with no check pending and no required check failed; carries the base, the merge
#              state, who approved it (approved_by), the checks counted by conclusion (checks), each open
#              thread (where, who, its first line), and each check not required that failed or warns
#              (warnings: name, conclusion, url, and the title and annotations of one that warns), with
#              changed_files when there is a warning
# Required means the base branch requires the check; when it requires none, every check is required.
#   MERGED     merged, and every run its merge commit started on the base (the Release, an infrastructure
#              apply) passed or was skipped
#   RELEASE_FAILED  merged, but a run its merge commit started on the base failed, or had not finished
#              after an hour; the runs are listed
#   CLOSED
#   FIX_CLOSED  the pull request named by --fixed-by was closed without being merged
#   FIX_FAILED  the pull request named by --fixed-by was merged, but a run its merge commit started
#              failed, or had not finished an hour after it started; the runs are listed
# A commit whose type releases nothing still runs the Release, whose publish job is then skipped, so
# the merge waits for those runs whatever the commit's type.
# A branch only behind its base is brought up to date here (`gh pr update-branch`, which keeps the
# approval) and the watch goes on. While Claude Code Review runs on the head commit, it waits.
# Answered means the last word is yours: a thread whose last comment is yours, a top-level comment
# older than your last top-level comment, or a check that warns and completed before it.
# With --fixed-by <fix> (a URL of any repo, or a number of the same repo), the pull request waits for
# <fix>, the one that fixes a failure its base also has. Once <fix> is merged and the runs its merge
# commit started passed, the fix is brought here and the checks run again:
#   same repo   `gh pr update-branch`, unless the branch holds the merge commit already: a base that
#               does not require branches to be up to date never reports BEHIND, so the merge alone
#               reruns nothing;
#   other repo  `gh run rerun --failed` on each GitHub Actions run holding a failed job that
#               CI_FAILED counts and that started before those runs ended.
# From there it is watched as without --fixed-by.
# When several verdicts apply, the first in the order CONFLICT, FIX_CLOSED, FIX_FAILED,
# FIX_MERGED, CI_FAILED, COMMENTS, BEHIND, APPROVED is given; FIX_MERGED and BEHIND print nothing,
# they are the updates and reruns above. A verdict this Claude Code session already got is not printed again:
# the next one that applies is given instead, or the watch goes on until the pull request changes, so
# an item held for the user, a merge.sh refusal or a failed fix does not come back at once. MERGED,
# RELEASE_FAILED and CLOSED always print.
# CI_FAILED gives each failed GitHub Actions job its `##[error]` lines (errors) and the file holding
# its failed steps' log (log).
# Usage: watch-pr.sh <pr url> [--fixed-by <fix>] [--max-wait <seconds>]. With --max-wait, after that many
# seconds with nothing to act on it prints {"verdict":"WAIT"} and exits, so a caller that must run it
# in the foreground runs it again.
set -euo pipefail
usage() { echo "usage: watch-pr.sh <pr url> [--fixed-by <pr url or number>] [--max-wait <seconds>]" >&2; exit 2; }
pr="${1:-}"
[[ "$pr" =~ ^https://github\.com/[^/]+/[^/]+/pull/[0-9]+/?$ ]] || { echo "give the pull request's URL, not \"$pr\": a number alone means a different pull request in each repo the shell may be in" >&2; usage; }
shift
max_wait=""
fix=""
fix_repo=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --max-wait) max_wait="$2"; shift 2 ;;
    --fixed-by)
      if [[ "${2:-}" =~ ^[0-9]+$ ]]; then fix="$2"
      elif [[ "${2:-}" =~ ^https://github\.com/([^/]+)/([^/]+)/pull/([0-9]+)/?$ ]]; then
        fix_repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"; fix="${BASH_REMATCH[3]}"
      else usage
      fi
      shift 2 ;;
    *) usage ;;
  esac
done
deadline=$(( $(date +%s) + ${max_wait:-0} ))
timed_out() { [ -n "$max_wait" ] && [ "$(date +%s)" -ge "$deadline" ]; }
# Sleeps the given seconds, or less when the --max-wait deadline comes first.
nap() {
  local s="$1"
  [ -n "$max_wait" ] && [ $(( deadline - $(date +%s) )) -lt "$s" ] && s=$(( deadline - $(date +%s) ))
  [ "$s" -gt 0 ] && sleep "$s"
  return 0
}

# Runs gh again when it fails, as the network often does, up to ten tries or the --max-wait
# deadline; then it returns gh's failure.
gh_read() {
  for _ in 1 2 3 4 5 6 7 8 9; do
    gh "$@" 2>/dev/null && return
    timed_out && return 1
    nap 30
  done
  gh "$@"
}

# Adds errors and log to each failed check that is a GitHub Actions job.
ci_logs() {
  local out="$1" url run job log errors
  while read -r url; do
    [[ "$url" =~ /actions/runs/([0-9]+)/job/([0-9]+) ]] || continue
    run="${BASH_REMATCH[1]}"; job="${BASH_REMATCH[2]}"
    log="$dir/job-$job.log"
    gh_read run view "$run" -R "$owner/$name" --job "$job" --log-failed >"$log" || continue
    errors=$(perl -ne 's/\e\[[0-9;]*m//g; print "$1\n" if /##\[error\](.*)/' "$log" \
      | awk '!seen[$0]++ && n++ < 10' | jq -R . | jq -s .)
    out=$(jq --arg url "$url" --arg log "$log" --argjson errors "$errors" \
      '.checks |= map(if .url == $url then . + {errors: $errors, log: $log} else . end)' <<<"$out")
  done < <(jq -r '.checks[].url // empty' <<<"$out")
  printf '%s\n' "$out"
}

read -r owner name number < <(gh_read pr view "$pr" --json url,number \
  -q '[(.url | split("/")[3]), (.url | split("/")[4]), .number] | @tsv')
tmp="${TMPDIR:-/tmp}"
dir="${tmp%/}/pr-babysit/$owner-$name-$number"
mkdir -p "$dir"
seen="$dir/seen-${CLAUDE_CODE_SESSION_ID:-}"
fix_repo="${fix_repo:-$owner/$name}"
# A wrong --fixed-by fails here, not as a watch that never ends.
[ -z "$fix" ] || gh_read pr view "$fix" -R "$fix_repo" --json url >/dev/null
updated_for=""
# The checks the base branch requires. When the rules cannot be read the list is empty, and every
# check is required.
base=$(gh_read pr view "$pr" --json baseRefName -q .baseRefName)
required=$(gh api "repos/$owner/$name/rules/branches/$base" \
  --jq '[.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context]' \
  2>/dev/null) || required='[]'
[ -n "$required" ] || required='[]'

query='query($owner: String!, $name: String!, $number: Int!, $fixOwner: String!, $fixName: String!,
    $fix: Int!, $hasFix: Boolean!) {
  viewer { login }
  fixRepo: repository(owner: $fixOwner, name: $fixName) @include(if: $hasFix) {
    pullRequest(number: $fix) { state url mergedAt mergeCommit { oid } }
  }
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      state url reviewDecision mergeStateStatus headRefOid baseRefName mergeCommit { oid }
      commits(last: 1) { nodes { commit { statusCheckRollup { contexts(first: 100) { nodes {
        __typename
        ... on CheckRun { name status conclusion detailsUrl startedAt databaseId title summary completedAt }
        ... on StatusContext { context state targetUrl }
      } } } } } }
      comments(last: 50) { nodes { databaseId url body createdAt author { __typename login } } }
      reviews(last: 50) { nodes { databaseId url state body submittedAt author { __typename login } } }
      reviewThreads(first: 100) { nodes { id isResolved path line
        comments(first: 50) { nodes { databaseId url body createdAt author { __typename login } } } } }
    }
  }
}'

# A check that ended neutral, or passed with a title that says it failed. Which of its annotations
# count is read apart, once per check run.
warns='def failedTitle: .title // "" | test("\\bfail"; "i");
  def warns: .__typename == "CheckRun" and .status == "COMPLETED"
    and (.conclusion == "NEUTRAL" or (.conclusion == "SUCCESS" and failedTitle));'

verdict='
  def required: ($required | length) == 0 or ((.name // .context) as $n | $required | index($n) != null);
  .data.viewer.login as $me
  | .data.fixRepo.pullRequest as $fix
  | .data.repository.pullRequest as $p
  | ($p.commits.nodes[0].commit.statusCheckRollup.contexts.nodes // []) as $checks
  | ($checks | map(select(.__typename == "CheckRun"
      and .name == "Claude Code Review" and .status != "COMPLETED")) | length > 0) as $reviewing
  # A workflow started twice for one commit shows each check twice; the run cancelled as a duplicate is no
  # failure when its twin passed.
  | ($checks | map(select(.__typename == "CheckRun" and .conclusion == "SUCCESS") | .name)) as $passed
  | ($checks | map(select(
        (.__typename == "CheckRun" and (.conclusion // "" | IN("FAILURE","TIMED_OUT","CANCELLED","ACTION_REQUIRED","STARTUP_FAILURE"))
          and (.conclusion == "CANCELLED" and (.name | IN($passed[])) | not))
        or (.__typename == "StatusContext" and (.state | IN("FAILURE","ERROR")))))) as $red
  | ($red | map(select(required))) as $failedChecks
  | ($failedChecks | map({name: (.name // .context), url: (.detailsUrl // .targetUrl)})) as $failed
  | ([$red[] | select(required | not)
       | {name: (.name // .context), conclusion: (.conclusion // .state), url: (.detailsUrl // .targetUrl)}]
     + [$checks[] | select(warns and (required | not))
       | ($annotations[.databaseId | tostring] // []) as $a
       | select(($a | length) > 0 or failedTitle)
       | {name, conclusion, url: .detailsUrl, title, annotations: $a}]) as $warnings
  | ($checks | map(select(
        (.__typename == "CheckRun" and .status != "COMPLETED")
        or (.__typename == "StatusContext" and (.state | IN("PENDING","EXPECTED"))))) | length) as $pending
  | ([($p.comments.nodes[] | select(.author.login == $me) | .createdAt),
      ($p.reviews.nodes[] | select(.author.login == $me) | .submittedAt)] | max // "") as $mine
  | ([$p.reviewThreads.nodes[]
      | select(.isResolved | not)
      | select(.comments.nodes[0].author.login == "claude" or .comments.nodes[0].author.__typename == "User")
      | select(.comments.nodes[-1].author.login != $me)
      | {kind: "thread", thread: .id, comment: .comments.nodes[0].databaseId, path, line,
         author: .comments.nodes[-1].author.login, url: .comments.nodes[0].url,
         severity: ((.comments.nodes[0].body | capture("bhfn:[0-9]+:(?<s>[a-z_]+)").s // "")
           | if . == "normal" then "important" elif . == "" then null else . end),
         body: ([.comments.nodes[] | "## \(.author.login)\n\n\(.body)\n"] | join("\n"))}]
     + [$p.comments.nodes[]
      | select(.author.__typename == "User" and .author.login != $me and .createdAt > $mine)
      | {kind: "comment", comment: .databaseId, author: .author.login, url, body: "## \(.author.login)\n\n\(.body)\n"}]
     + [$p.reviews.nodes[]
      | select(.author.__typename == "User" and .author.login != $me and .submittedAt > $mine)
      | select(.state == "CHANGES_REQUESTED" or (.state == "COMMENTED" and (.body | length) > 0))
      | {kind: "review", comment: .databaseId, author: .author.login, url, body: "## \(.author.login) (\(.state))\n\n\(.body)\n"}]
     + [$checks[]
      | select(warns and required and .completedAt > $mine)
      | ($annotations[.databaseId | tostring] // []) as $a
      | select(($a | length) > 0 or failedTitle)
      | {kind: "check", check: .databaseId, name, url: .detailsUrl, annotations: $a,
         body: ("## \(.name)\n\n\(.title // "")\n\n\(.summary // "")\n\n"
           + ($a | map("- \(.path):\(.line) \(.message)\n") | add // ""))}]
    ) as $items
  | if $p.state != "OPEN" then {verdict: $p.state, pr: $p.url, commit: $p.mergeCommit.oid}
    elif $reviewing then empty
    else
      (if $p.mergeStateStatus == "DIRTY" then {verdict: "CONFLICT", pr: $p.url, head: $p.headRefOid} else empty end),
      (if $fix.state == "CLOSED" then {verdict: "FIX_CLOSED", pr: $p.url, fix: $fix.url} else empty end),
      (if $fix.state == "MERGED" then
        ($fixRuns | map(select(.status != "completed"
          or (.conclusion | IN("success", "skipped", "neutral") | not)))) as $bad
        # The fix is in once the last of those runs ended, or at the merge for a repo with none.
        | ([$fixRuns[].updated] | max // $fix.mergedAt) as $fixedAt
        # A repo with none shows none within 10 minutes.
        | if ($fixRuns | length) == 0 and now - ($fix.mergedAt | fromdateiso8601) < 600 then empty
          elif any($fixRuns[]; .status != "completed" and now - (.started | fromdateiso8601) < 3600) then empty
          elif ($bad | length) > 0 then
            {verdict: "FIX_FAILED", pr: $p.url, fix: $fix.url, runs: ($bad | map(del(.started, .updated)))}
          else
            {verdict: "FIX_MERGED", merge: $fix.mergeCommit.oid, head: $p.headRefOid,
             reruns: [$failedChecks[] | select(.__typename == "CheckRun" and .startedAt < $fixedAt)
               | .detailsUrl | capture("/actions/runs/(?<run>[0-9]+)/").run] | unique}
          end
       else empty end),
      (if ($failed | length) > 0 and $pending == 0 then {verdict: "CI_FAILED", pr: $p.url, checks: $failed} else empty end),
      (if ($items | length) > 0 then {verdict: "COMMENTS", pr: $p.url, items: $items} else empty end),
      (if $p.mergeStateStatus == "BEHIND" then {verdict: "BEHIND", head: $p.headRefOid} else empty end),
      (if $p.reviewDecision == "APPROVED" and $pending == 0 and ($failed | length) == 0 then
        {verdict: "APPROVED", pr: $p.url, base: $p.baseRefName, merge_state: $p.mergeStateStatus,
         approved_by: ([$p.reviews.nodes[] | select(.state == "APPROVED") | .author.login] | unique),
         checks: ($checks | group_by(.conclusion // .state)
           | map({key: (.[0].conclusion // .[0].state), value: length}) | from_entries),
         open_threads: [$p.reviewThreads.nodes[] | select(.isResolved | not)
           | {url: .comments.nodes[0].url, path, line, author: .comments.nodes[0].author.login,
              last_word: .comments.nodes[-1].author.login,
              first_line: (.comments.nodes[0].body | split("\n")[0] | .[0:200])}],
         warnings: $warnings}
       else empty end)
    end'

while true; do
  timed_out && { echo '{"verdict":"WAIT"}'; exit 0; }
  state=$(gh_read api graphql -F owner="$owner" -F name="$name" -F number="$number" \
    -F fixOwner="${fix_repo%/*}" -F fixName="${fix_repo#*/}" -F fix="${fix:-0}" \
    -F hasFix="$([ -n "$fix" ] && echo true || echo false)" -f query="$query") || { nap 60; continue; }
  # The runs the --fixed-by merge commit started.
  fix_runs='[]'
  fix_merge=$(jq -r '.data.fixRepo.pullRequest | select(.state == "MERGED") | .mergeCommit.oid' <<<"$state")
  if [ -n "$fix" ] && [ -n "$fix_merge" ]; then
    fix_runs=$(gh_read api "repos/$fix_repo/actions/runs?head_sha=$fix_merge&event=push" \
      -q '[.workflow_runs[] | {name, status, conclusion, attempt: .run_attempt, url: .html_url,
        started: .run_started_at, updated: .updated_at}]') || { nap 60; continue; }
  fi
  # The warning and failure annotations of each check that warns. A completed check run never changes
  # and a rerun makes a new one, so each is read once.
  annotations='{}'
  for id in $(jq -r "$warns"' .data.repository.pullRequest.commits.nodes[0].commit.statusCheckRollup.contexts.nodes // []
      | .[] | select(warns) | .databaseId' <<<"$state"); do
    file="$dir/annotations-$id.json"
    [ -s "$file" ] || { gh_read api "repos/$owner/$name/check-runs/$id/annotations?per_page=100" \
      -q '[.[] | select(.annotation_level | IN("warning", "failure")) | {path, line: .start_line, message}]' \
      >"$file.part" && mv "$file.part" "$file"; } || { nap 60; continue 2; }
    annotations=$(jq --arg id "$id" --slurpfile a "$file" '. + {($id): $a[0]}' <<<"$annotations")
  done
  # The verdicts that apply, one per line in the order above.
  candidates=$(jq -c --argjson fixRuns "$fix_runs" --argjson required "$required" \
    --argjson annotations "$annotations" "$warns$verdict" <<<"$state")
  v=WAIT
  while IFS= read -r out; do
    [ -n "$out" ] || continue
    key=$(shasum <<<"$out")
    v=$(jq -r .verdict <<<"$out")
    case "$v" in MERGED|CLOSED) break ;; esac
    grep -qxF "$key" "$seen" 2>/dev/null || break
    v=WAIT
  done <<<"$candidates"
  case "$v" in
    WAIT) ;;
    BEHIND)
      head=$(jq -r .head <<<"$out")
      if [ "$head" != "$updated_for" ]; then
        gh_read pr update-branch "$pr" >/dev/null && updated_for="$head"
      fi ;;
    FIX_MERGED)
      if [ "$fix_repo" = "$owner/$name" ]; then
        behind=$(gh_read api "repos/$owner/$name/compare/$(jq -r .merge <<<"$out")...$(jq -r .head <<<"$out")" \
          -q .behind_by) || { nap 60; continue; }
        [ "$behind" -eq 0 ] || gh_read pr update-branch "$pr" >/dev/null || { nap 60; continue; }
      else
        for run in $(jq -r '.reruns[]' <<<"$out"); do
          gh_read run rerun "$run" --failed -R "$owner/$name" >/dev/null || { nap 60; continue 2; }
        done
      fi
      fix="" ;;
    COMMENTS)
      echo "$key" >>"$seen"
      # Each item's text goes to a file, read as data: never paste it into a command.
      jq -c '.items[]' <<<"$out" | while read -r item; do
        jq -r .body <<<"$item" >"$dir/$(jq -r '.comment // "check-\(.check)"' <<<"$item").md"
      done
      jq --arg dir "$dir" '.items |= map(del(.body) + {text: "\($dir)/\(.comment // "check-\(.check)").md"})' <<<"$out"
      exit 0 ;;
    MERGED)
      # Waits for the runs the merge commit started on the base; a repo with none shows none within
      # 10 minutes.
      commit=$(jq -r .commit <<<"$out")
      for waited in $(seq 0 60 3600); do
        timed_out && { echo '{"verdict":"WAIT"}'; exit 0; }
        runs=$(gh_read api "repos/$owner/$name/actions/runs?head_sha=$commit&event=push" \
          -q '[.workflow_runs[] | {name, status, conclusion, url: .html_url}]') \
          || { timed_out && { echo '{"verdict":"WAIT"}'; exit 0; }; nap 60; continue; }
        if [ "$(jq length <<<"$runs")" -gt 0 ]; then
          [ "$(jq 'map(select(.status != "completed")) | length' <<<"$runs")" -eq 0 ] && break
        elif [ "$waited" -ge 600 ]; then
          break
        fi
        nap 60
      done
      jq --argjson runs "$runs" '
        ($runs | map(select(.status != "completed"
          or (.conclusion | IN("success", "skipped", "neutral") | not)))) as $failed
        | if ($failed | length) > 0 then . + {verdict: "RELEASE_FAILED", runs: $failed} else . end' <<<"$out"
      exit 0 ;;
    CI_FAILED)
      files=$(gh_read api "repos/$owner/$name/pulls/$number/files" --paginate -q '.[].filename' \
        | jq -R . | jq -s .) || { nap 60; continue; }
      echo "$key" >>"$seen"
      ci_logs "$out" | jq --argjson files "$files" '. + {changed_files: $files}'
      exit 0 ;;
    APPROVED)
      if [ "$(jq '.warnings | length' <<<"$out")" -gt 0 ]; then
        files=$(gh_read api "repos/$owner/$name/pulls/$number/files" --paginate -q '.[].filename' \
          | jq -R . | jq -s .) || { nap 60; continue; }
        out=$(jq --argjson files "$files" '. + {changed_files: $files}' <<<"$out")
      fi
      echo "$key" >>"$seen"; jq . <<<"$out"; exit 0 ;;
    *) echo "$key" >>"$seen"; jq . <<<"$out"; exit 0 ;;
  esac
  nap 60
done
