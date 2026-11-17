#!/usr/bin/env bash
# Starts a run on a Linear card: writes the card to the task folder's task.md, moves the card to
# In Progress when no one has started it, and prints the task folder, the state, the blockers that
# are not completed, and task.md. A card with such a blocker moves only with --start, once the
# caller has decided the blocker does not stop the run.
# Usage: WORKSPACE=<folder of the repos> start-task.sh <task id> [--start]
# A task.md that already exists is kept: a run that starts again keeps what it added to it.
# Linear is read with the user's API key, from the Keychain item linear-api-key (see /geovane:setup).
set -euo pipefail
id="$1"
force="${2:-}"
folder="${WORKSPACE:?set WORKSPACE to the folder that holds the repos}/.runs/$id"
key=$(security find-generic-password -a "$USER" -s linear-api-key -w)

# Runs one GraphQL call; Linear often fails once, so a failure is tried once more.
linear() {
  local body out
  body=$(jq -n --arg q "$1" --argjson v "$2" '{query: $q, variables: $v}')
  for try in 1 2; do
    if out=$(curl -sf https://api.linear.app/graphql -H "Authorization: $key" \
        -H 'Content-Type: application/json' -d "$body") && [ "$(jq '.errors | length' <<<"$out")" = 0 ]; then
      printf '%s\n' "$out"
      return
    fi
    if jq -e '[.errors[]?.message] | any(test("Entity not found"))' <<<"${out:-{\}}" >/dev/null 2>&1; then
      echo "STOP: Linear has no card $id" >&2
      exit 1
    fi
    [ "$try" = 1 ] && sleep 5
  done
  echo "STOP: Linear failed twice for $id: ${out:-no answer}" >&2
  exit 1
}

issue=$(linear 'query($id: String!) { issue(id: $id) {
  identifier title description url state { name type } parent { identifier }
  relations { nodes { type relatedIssue { identifier } } }
  inverseRelations { nodes { type issue { identifier title state { name type } } } }
  team { states { nodes { id name type position } } } } }' "$(jq -n --arg id "$id" '{id: $id}')" | jq '.data.issue')

mkdir -p "$folder"
if [ -e "$folder/task.md" ]; then
  kept=" (kept: it already existed)"
else
  kept=""
  jq -r '
    ([.parent.identifier // empty | "Parent: \(.)"]
     + [[.relations.nodes[] | select(.type == "blocks") | .relatedIssue.identifier] | select(length > 0) | "Blocks: \(join(", "))"]
     + [[.inverseRelations.nodes[] | select(.type == "blocks") | .issue.identifier] | select(length > 0) | "Blocked by: \(join(", "))"]
     + [[(.relations.nodes[] | select(.type == "related") | .relatedIssue.identifier),
         (.inverseRelations.nodes[] | select(.type == "related") | .issue.identifier)] | select(length > 0) | "Related: \(join(", "))"]
    ) as $links
    | "# \(.identifier) — \(.title)\n\n\(.url)\n\($links | join(" · "))\n\n\(.description // "")"' <<<"$issue" >"$folder/task.md"
fi

state=$(jq -r '"\(.state.name) (\(.state.type))"' <<<"$issue")
open=$(jq '[.inverseRelations.nodes[] | select(.type == "blocks" and .issue.state.type != "completed")] | length' <<<"$issue")
case "$(jq -r .state.type <<<"$issue")" in
  backlog|unstarted|triage)
    if [ "$open" -gt 0 ] && [ "$force" != --start ]; then
      state="$state, not moved: it has open blockers"
    else
      target=$(jq -r '[.team.states.nodes[] | select(.type == "started")] | sort_by(.position)
        | ((map(select(.name == "In Progress")) + .)[0]) | "\(.id) \(.name)"' <<<"$issue")
      linear 'mutation($id: String!, $s: String!) { issueUpdate(id: $id, input: { stateId: $s }) { success } }' \
        "$(jq -n --arg id "$id" --arg s "${target%% *}" '{id: $id, s: $s}')" >/dev/null
      state="$state → ${target#* }"
    fi ;;
  *) state="$state, left as it is" ;;
esac

echo "task folder: $folder"
echo "state: $state"
jq -r '[.inverseRelations.nodes[] | select(.type == "blocks" and .issue.state.type != "completed")
  | "  \(.issue.identifier) (\(.issue.state.name)): \(.issue.title)"]
  | if length == 0 then "open blockers: none" else "open blockers:\n" + join("\n") end' <<<"$issue"
echo "--- task.md$kept"
cat "$folder/task.md"
