#!/usr/bin/env bash
# Prints the Depends on section of a pull request body (on stdin), one "<url> <condition>" per line.
# The condition is what this pull request waits for, not the dependency's state today: "merged" or
# "deployed in <env>", written (needs it merged) or (needs it deployed in <env>); empty when the bullet
# names none. The older marks (merged) and (deployed in <env>) still count.
# Usage: deps.sh < body
set -euo pipefail
BODY="$(cat)" python3 - <<'EOF'
import os, re
m = re.search(r"^## Depends on\s*\n(.*?)(?=^## |\Z)", os.environ["BODY"], re.S | re.M)
for line in (m.group(1) if m else "").splitlines():
    url = re.search(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+", line)
    condition = re.search(r"\((?:needs it )?(merged|deployed in [a-z]+)\)", line)
    if url:
        print(url.group(0), condition.group(1) if condition else "")
EOF
