#!/usr/bin/env bash
# Prints a harness file whole, then every harness file that names it, for harness-change step 1.
# Usage: harness-read.sh <file>
# A skill or an agent is named by its `name:`, as **name**, `name`, skills/name/ or agents/name.md;
# any other file by its file name. The harness is the user's config folder and this plugin.
set -euo pipefail
file=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
config="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
plugin=$(cd "$(dirname "$0")/../../../.." && pwd)
name=$(sed -n 's/^name: *//p' "$file" | head -1)
if [ -n "$name" ]; then
  pattern="\*\*$name\*\*|\`(geovane:)?$name\`|skills/$name/|agents/$name\.md|$name (skill|agent)"
else
  pattern=$(basename "$file" | sed 's/\./\\./g')
fi
echo "=== $file"
cat -n "$file"
echo
echo "=== files that name it ($pattern)"
grep -rlE --exclude-dir=node_modules --exclude-dir=plugins --exclude-dir=projects -e "$pattern" \
  "$config/skills" "$config/agents" "$config/hooks" "$config/settings.json" "$config/CLAUDE.md" \
  "$plugin/skills" "$plugin/agents" "$plugin/hooks" 2>/dev/null | grep -v -x "$file" || echo "(none)"
