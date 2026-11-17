#!/usr/bin/env python3
"""PreToolUse hook on the Agent tool: every spawn of this plugin's agents runs on a model and effort someone chose.

An agent of the plugin with a frontmatter (engineer, judge, cleaner and the rest) takes its model and
effort from it: a call that tries to override them is denied. The delegate (atlas-agent) serves
every kind of job, so it has none: without a model and an effort in the call it takes the
session's, often Opus at xhigh. Its call is denied until it names both, between sonnet at medium
and opus at high.

A spawn that leaves out run_in_background gets it set to false, so it runs in the foreground. The
tool's default is the background, where each agent's end wakes the caller for a turn that only waits.

Spawns of any other agent pass untouched: a plugin hook fires in the whole session.
"""
import json
import sys

PLUGIN = 'geovane'
DELEGATE = f'{PLUGIN}:atlas-agent'
MODELS = ('sonnet', 'opus')
EFFORTS = ('medium', 'high')
GUIDE = (
    'Pick the cheapest that does the job: sonnet for lookups, reading, writing and '
    'analysis; opus when the task needs judgment across many pieces. Effort medium by '
    'default, high when the task needs reasoning across many pieces. Raise a step when the '
    'result is hard to check; lower a step when a script or a test will check it.'
)


def allowed_model(model):
    model = model.lower()
    return model in MODELS or any(model.startswith('claude-' + m) for m in MODELS)


def foreground(tool_input):
    """A spawn that does not choose runs in the foreground: the caller waits in the call, not in turns."""
    if 'run_in_background' in tool_input:
        return 0
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'updatedInput': {**tool_input, 'run_in_background': False},
    }}))
    return 0


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': reason,
    }}))
    return 0


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get('tool_name') not in ('Agent', 'Task'):
        return 0
    tool_input = data.get('tool_input') or {}
    agent_type = tool_input.get('subagent_type') or ''
    if not agent_type.startswith(PLUGIN + ':'):
        return 0
    model = tool_input.get('model')
    effort = tool_input.get('effort')

    if agent_type != DELEGATE:
        if model or effort:
            return deny(
                f'{agent_type} takes its model and effort from its frontmatter. '
                'Call it again without model and effort.'
            )
        return foreground(tool_input)

    if not model or not effort:
        return deny(
            f'{DELEGATE} has no model and effort of its own: choose them for this task and call it '
            f'again with both. Allowed: model {"/".join(MODELS)}, effort {"/".join(EFFORTS)}. {GUIDE}'
        )
    if not allowed_model(model) or effort not in EFFORTS:
        return deny(
            f'model={model} effort={effort} is outside the bounds for {DELEGATE} (sonnet or opus, '
            f'effort medium or high). Call it again within them. {GUIDE}'
        )
    return foreground(tool_input)


if __name__ == '__main__':
    sys.exit(main())
