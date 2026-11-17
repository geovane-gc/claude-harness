---
name: setup
description: Checks and sets up what the geovane plugin needs on this machine (claude.ai connectors, the Linear key, the repos folder, command-line tools) and says what is missing. Safe to run again.
disable-model-invocation: true
---

# Set up the geovane plugin

Check each item below in order and fix what you can. Run everything again on a second call: each
check reads before it writes, and a passing check changes nothing.

Never ask the user to paste a secret into the chat. A secret goes into the Keychain by a command the
user runs with the `!` prefix, so it lands in their shell, not in the conversation.

## 1. claude.ai connectors

The engine reads Linear cards and sends Slack messages through the user's claude.ai connectors.
Run ToolSearch with `select:mcp__claude_ai_Linear__get_issue,mcp__claude_ai_Slack__slack_send_message`.
For each one not found: connect it at claude.ai → Settings → Connectors, then run `/login` here
and start a new session. Slack is optional: without it, the playbooks put in the reply what they
would have sent.

## 2. Linear API key

`/geovane:engage` starts a run on a card with a script that calls Linear's API with the user's
key. Check it with `security find-generic-password -a "$USER" -s linear-api-key >/dev/null && echo ok`.
Missing: the user creates a personal key at linear.app → Settings → Security & access → Personal
API keys, then runs `! security add-generic-password -a "$USER" -s linear-api-key -w` and pastes
the key at the prompt.

## 3. Repos folder

Runs read the repos and keep their notes under this folder: `${user_config.workspace}`. When that
path still reads as a `${...}` placeholder, the option was never saved, and every skill of the plugin
sees the placeholder instead of a folder. Otherwise check that it exists and holds the repos. Either
way, a fix is the user setting **Repos folder** in `/config`, under the geovane plugin (usually
`~/projects`), then starting a new session.

## 4. Command-line tools

Check with `command -v`: `git`, `gh`, `jq`, `python3`, `docker`. Missing one: give its install
command (`brew install gh jq`; Docker Desktop for `docker`). Check `gh auth status`; logged out:
`! gh auth login`.

## 5. What the plugin's hooks do

Tell the user, once, what changes in their sessions:

- Inside this plugin's agents, `git push --force`, `rm -r`, `git reset --hard` and other commands
  that throw away work are blocked, with the recoverable way in the message.
- A spawn of `geovane:atlas-agent` must name a model (sonnet or opus) and an effort (medium or
  high); the plugin's other agents keep the model and effort of their own definition.

Nothing outside the plugin's agents is blocked.

## Answer

One line per item: ✅ ready, or ❌ with the one command or step that fixes it.
