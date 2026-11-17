#!/usr/bin/env bash
# Checks one commit subject or PR title. Prints "ok", or what to fix and exits 1.
title="$1"
# A trailing task id, such as " (ENG-450)", is the card's link: it counts for neither the length nor the period.
task_suffix='[[:space:]]\([A-Z][A-Z0-9]*-[0-9]+\)$'
if [[ "$title" =~ $task_suffix ]]; then
  title="${title%"${BASH_REMATCH[0]}"}"
fi

format='^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9][a-z0-9-]*\))?!?: [a-z]'
if [[ ! "$title" =~ $format ]]; then
  echo "The title follows <type>(<scope>): <description>, with type in build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test and the description starting in lowercase."
  exit 1
fi

if (( ${#title} > 60 )); then
  echo "The title has ${#title} characters and fits in 60."
  exit 1
fi

description="${title#*: }"

if [[ "$description" == *. ]]; then
  echo "The description ends without a period."
  exit 1
fi

first="${description%% *}"
case "$first" in
  the|a|an|every|each|one|what|no|its|his|her|their|this|that|these|those|all|some|any)
    echo "The description starts with a verb in the imperative: \"If applied, this commit will <description>\"."
    exit 1
    ;;
esac

case "$first" in
  embed|feed|need|seed|shed|speed|bring|ping|ring|string) ;;
  *ed|*ing)
    echo "\"$first\" goes in the base form of the verb, as in \"If applied, this commit will <description>\"."
    exit 1
    ;;
esac

echo "ok"
