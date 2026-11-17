#!/usr/bin/env python3
"""PostToolUse hook on the Skill tool: a pull request this plugin's commit skill opens in the main session gets
its watcher at once.

The commit skill answers `opened <url>` for each pull request it opened. The main session starts the PR
babysit playbook on it at once (watch-pr.sh in the background), whatever playbook it runs and whatever
the repo, docs and deploy config included. A run that waits for a later step or for the user leaves the pull
request's reviews and checks unanswered. Inside a subagent the caller owns the watch, so the hook stays silent there.
"""
import json
import os
import re
import sys

# The plugin's folder: this file sits in its hooks/scripts/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
WATCH = os.path.join(ROOT, 'skills', 'engine', 'engage', 'scripts', 'watch-pr.sh')
OPENED = re.compile(r'\bopened\s+(https://github\.com/[\w.-]+/[\w.-]+/pull/\d+)')


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get('tool_name') != 'Skill' or data.get('agent_id'):
        return 0
    # A plugin skill is named with the plugin's prefix; a bare `commit` is another commit skill.
    if (data.get('tool_input') or {}).get('skill') != 'geovane:commit':
        return 0
    response = data.get('tool_response')
    # A forked skill answers {'status': 'forked', 'result': '<text>'}: read the text itself, since
    # json.dumps turns its line breaks into \n and `opened` after one no longer matches.
    if isinstance(response, dict) and isinstance(response.get('result'), str):
        response = response['result']
    text = response if isinstance(response, str) else json.dumps(response)
    urls = list(dict.fromkeys(OPENED.findall(text)))
    if not urls:
        return 0
    calls = '; '.join(f'`{WATCH} {url}`' for url in urls)
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PostToolUse',
        'additionalContext': (
            f'The commit skill opened {len(urls)} pull request(s). Start the PR babysit playbook on each now, '
            f'before any other step and without asking: run {calls}, each with Bash run_in_background '
            '(PR babysit step 2), then go on with the run; each verdict wakes you. Read no pull request state '
            "yourself (`gh pr view`, `gh pr checks`): take each one's number, branch and base from the commit "
            "skill's answer, and its state from the verdict."
        ),
    }}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
