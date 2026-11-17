#!/usr/bin/env python3
"""PreToolUse hook on the Agent tool: refuses at spawn of one of this plugin's agents what would fail inside
it, and says the way that works.

- isolation "worktree" for an agent that opens its own worktree (its definition runs worktree.sh): the
  harness pins the agent to a worktree of the caller's current repo and refuses git anywhere else, so an
  agent sent to another repo stops half done.
- A brief that asks the agent to write a .md file whose name starts with report, summary, findings or
  analysis: Claude Code refuses that Write in every subagent, so the agent pastes the text back and the
  caller writes it again. Only the prompt is read: a file it names may hold a brief meant for another
  agent (a findings file an earlier agent was asked to write).
"""
import json
import os
import re
import sys

REPORT_NAME = r'(?:report|summary|findings|analysis)[^\s/`\'")\]]*\.md'
PATH = rf'(?:[^\s`\'"(]*/)?{REPORT_NAME}'
WRITE_REPORT = re.compile(
    r'\b(?:write|save)\s+'
    r'(?:(?:your|the|its|their|all)\s+)?'
    r'(?:(?:findings|report|summary|analysis|results?|answer|output)\s+(?:to|in|into|as)\s+)?'
    rf'[`\'"]?({PATH})',
    re.IGNORECASE,
)


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }}))
    return 0


PLUGIN = 'geovane:'
# The plugin's folder: this file sits in its hooks/scripts/.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))


def opens_own_worktree(agent_type):
    path = os.path.join(ROOT, 'agents', agent_type[len(PLUGIN):] + '.md')
    if not os.path.isfile(path):
        return False
    with open(path, encoding='utf-8') as f:
        return 'worktree.sh' in f.read()


def report_write(prompt):
    """The report-named file the prompt asks the agent to write, or None."""
    found = WRITE_REPORT.search(prompt)
    return found.group(1) if found else None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get('tool_name') not in ('Agent', 'Task'):
        return 0
    tool_input = data.get('tool_input') or {}
    agent_type = tool_input.get('subagent_type') or ''
    # A plugin hook fires in the whole session; only spawns of this plugin's agents are checked here.
    if not agent_type.startswith(PLUGIN):
        return 0

    if tool_input.get('isolation') == 'worktree' and opens_own_worktree(agent_type):
        return deny(
            f'BLOCKED: {agent_type} opens its own worktree with worktree.sh, in the repo its brief names. '
            'isolation "worktree" would pin it to a worktree of your current folder\'s repo and refuse git '
            'in any other. Spawn it again without isolation, naming the repo, and the worktree when it '
            'continues one.'
        )

    target = report_write(tool_input.get('prompt') or '')
    if target:
        return deny(
            f'BLOCKED: the brief asks the agent to write {target}. Claude Code refuses a subagent\'s Write '
            'to a .md file whose name starts with report, summary, findings or analysis. Ask for the '
            'findings as the agent\'s reply, and write the file yourself from it.'
        )
    return 0


if __name__ == '__main__':
    sys.exit(main())
