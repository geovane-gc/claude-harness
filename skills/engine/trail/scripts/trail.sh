#!/usr/bin/env bash
# Adds one note to a run's trail, <task folder>/trail.md, and prints the note's id.
# Usage: trail.sh <task folder> <kind> "<text>"
#        trail.sh <task folder> harness "<text>" [<diff file>]
#        trail.sh <task folder> settle <id> "<how it ended>"
# Kinds: decision fact problem docs skip harness info. A harness note takes its diff from a file,
# never from stdin: a caller's stdin can stay open with nothing in it, and reading it would hang.
# Each note is one line at the end of the file, "<id> <HH:MM UTC> <kind> <text>", with a harness
# note's diff below it, indented by four spaces. It is written under a lock, so notes written at
# the same time by several agents never overwrite each other.
set -euo pipefail
folder="$1"
kind="$2"
case "$kind" in
  decision|fact|problem|docs|skip|info) ref=""; text="$3" ;;
  harness)
    ref=""; text="$3"; diff_file="${4:-}"
    [ -z "$diff_file" ] || [ -f "$diff_file" ] || { echo "no diff file \"$diff_file\"" >&2; exit 1; }
    ;;
  settle) ref="$3 "; text="$4" ;;
  *) echo "kind is one of decision fact problem docs skip harness info settle, not \"$kind\"" >&2; exit 1 ;;
esac
mkdir -p "$folder"
file="$folder/trail.md"
lock="$folder/.trail.lock"
tries=0
until mkdir "$lock" 2>/dev/null; do
  # A lock older than 10 s belongs to a writer that died: take it over.
  tries=$((tries + 1)); [ "$tries" -gt 100 ] && { rmdir "$lock" 2>/dev/null || true; tries=0; }
  sleep 0.1
done
trap 'rmdir "$lock"' EXIT
id="n$(( $( (grep -c '^n[0-9]* ' "$file" 2>/dev/null) || true) + 1 ))"
note="$id $(date -u +%H:%M) $kind $ref$(tr '\n' ' ' <<<"$text" | sed 's/ *$//')"
if [ "$kind" = harness ] && [ -n "$diff_file" ]; then
  diff=$(sed 's/^/    /' "$diff_file")
  [ -n "$diff" ] && note="$note"$'\n'"$diff"
fi
printf '%s\n' "$note" >>"$file"
echo "$id"
