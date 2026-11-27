#!/bin/bash
set -euo pipefail
# Installs the agent from this folder into its own folder (outside the plugin cache) and fills in your config.
# usage: install.sh   (asks for each value; re-running never overwrites files you already have)
src=$(cd "$(dirname "$0")" && pwd)
ask() { local v; read -r -p "$1: " v; printf '%s' "${v:-${2:-}}"; }
HOME_DIR_NAME=$(ask "Folder name under your home for the agent [claude-code-agent]" "claude-code-agent")
AGENT_NAME=$(ask "Agent name, one word [Hermes]" "Hermes"); AGENT_EMOJI=$(ask "Agent emoji [🪽]" "🪽")
OWNER_NAME=$(ask "Your full name"); OWNER_FIRST_NAME=$(ask "Your first name"); OWNER_LAST_NAME=$(ask "Your last name")
OWNER_EMAIL=$(ask "Your work email (the one on your commits)")
ORGANIZATION_NAME=$(ask "Your organization's name as Slack shows it (people of another organization are not answered)")
SLACK_WORKSPACE_HOST=$(ask "Your Slack workspace host (e.g. yourteam.slack.com)")
GITHUB_ORG=$(ask "The GitHub organization of your repos (more go in github_orgs later)")
OWNER_GITHUB=$(ask "Your GitHub login"); OWNER_SLACK_ID=$(ask "Your Slack member ID (profile > ⋮ > Copy member ID)")
CONTROL_CHANNEL_NAME=$(ask "Name of a NEW private Slack channel only you are in (control channel)")
CONTROL_CHANNEL_ID=$(ask "Its channel ID (channel details > bottom)")
USER_GROUP_NAME=$(ask "A Slack user group you belong to whose mentions should count (or leave empty)")
USER_GROUP_ID=$(ask "Its ID (or empty)"); WATCHED_CHANNEL_ID=$(ask "Channel where CI announces new PRs (or empty)")
CI_BOT_ID=$(ask "That CI bot's user ID (or empty)")
CLAUDE_APP_USER_ID=$(ask "The Claude app's Slack user ID (read any message sent with Claude: *Sent using* <@THIS_ID|Claude>)")
dest="$HOME/$HOME_DIR_NAME"; mkdir -p "$dest/pepper/logs" "$dest/pepper/state"
rsync -a --ignore-existing --exclude install.sh "$src"/ "$dest"/
[ -f "$dest/pepper/config.json" ] || cp "$dest/config.example.json" "$dest/pepper/config.json"
export HOME_DIR_NAME AGENT_NAME AGENT_EMOJI OWNER_NAME OWNER_FIRST_NAME OWNER_LAST_NAME OWNER_EMAIL ORGANIZATION_NAME \
  SLACK_WORKSPACE_HOST GITHUB_ORG OWNER_GITHUB OWNER_SLACK_ID CONTROL_CHANNEL_NAME CONTROL_CHANNEL_ID USER_GROUP_NAME \
  USER_GROUP_ID WATCHED_CHANNEL_ID CI_BOT_ID CLAUDE_APP_USER_ID
python3 - "$dest" <<'PY'
import os, sys
root = sys.argv[1]
keys = ["HOME_DIR_NAME", "AGENT_NAME", "AGENT_EMOJI", "OWNER_NAME", "OWNER_FIRST_NAME", "OWNER_LAST_NAME", "OWNER_EMAIL",
        "ORGANIZATION_NAME", "SLACK_WORKSPACE_HOST", "GITHUB_ORG", "OWNER_GITHUB", "OWNER_SLACK_ID",
        "CONTROL_CHANNEL_NAME", "CONTROL_CHANNEL_ID", "USER_GROUP_NAME", "USER_GROUP_ID", "WATCHED_CHANNEL_ID", "CI_BOT_ID",
        "CLAUDE_APP_USER_ID"]
for base, _, files in os.walk(root):
    if "/repos" in base or "/state" in base or "/logs" in base:
        continue
    for name in files:
        path = os.path.join(base, name)
        try:
            text = open(path, encoding="utf-8").read()
        except UnicodeDecodeError:
            continue
        new = text
        for key in keys:
            new = new.replace("{{" + key + "}}", os.environ.get(key, ""))
        if new != text:
            open(path, "w", encoding="utf-8").write(new)
PY
CLAUDE_BIN=$(command -v claude || true) GH_BIN=$(command -v gh || true) python3 - "$dest/pepper/config.json" <<'PY'
import json, os, sys
path = sys.argv[1]
config = json.load(open(path))
for key, found in (("claude", os.environ.get("CLAUDE_BIN")), ("gh", os.environ.get("GH_BIN"))):
    if found:
        config[key] = found
for key, value in list(config.items()):
    if isinstance(value, dict):
        config[key] = {k: v for k, v in value.items() if k and v}
    elif isinstance(value, list):
        config[key] = [v for v in value if v != ""]
json.dump(config, open(path, "w"), indent=2, ensure_ascii=False)
PY
grep -qs "AGENT_HOME=" "$HOME/.zshenv" || printf '\nexport AGENT_HOME="%s"\n' "$dest" >> "$HOME/.zshenv"
echo "AGENT_HOME=$dest is in ~/.zshenv; the plugin's skills find the agent folder through it."
agent=$(printf '%s' "$AGENT_NAME" | tr '[:upper:]' '[:lower:]')
sed -e "s#__HOME__#$dest#g" -e "s#__AGENT__#$agent#g" "$dest/pepper/launchd/watch.plist.template" > "$dest/pepper/launchd/watch.plist"
chmod +x "$dest"/bin/* "$dest"/pepper/guard/*.py 2>/dev/null || true
# plugin/ is the geovane plugin, read from the agent's own clone of the harness repo (kept fresh by bin/repos sync):
# the build and review runs read the engage playbooks and agent-evolve there. Never edited from here.
harness=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("harness_repo",""))' "$dest/pepper/config.json")
if [ -n "$harness" ]; then
  "$dest/bin/repos" ensure "$harness" >/dev/null \
    || echo "Could not clone $harness (GitHub login?): run $dest/bin/repos ensure $harness later." >&2
  [ -L "$dest/plugin" ] || [ -e "$dest/plugin" ] || ln -s "repos/${harness##*/}" "$dest/plugin"
fi
for ignored in plugin repos/ worktrees/ pepper/logs/ pepper/state/ __pycache__/; do
  grep -qsxF "$ignored" "$dest/.gitignore" || printf '%s\n' "$ignored" >> "$dest/.gitignore"
done
cd "$dest" && { [ -d .git ] || git init -q; }
# The integrity check restores a protected file a run changed to its committed version: there must be one.
git rev-parse -q --verify HEAD >/dev/null || { git add -A && git -c user.name=Claude -c user.email=claude@localhost commit -qm "install"; }
echo "Installed in $dest. Next: README.md 'Depois' (claude login, gh, Keychain secrets, launchd)."
