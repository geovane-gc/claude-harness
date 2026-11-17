#!/usr/bin/env python3
"""PostToolUse hook on the Agent tool: after a background spawn, the caller waits for the agent's answer.

A background agent's answer arrives later as a message, at any depth.
A caller that keeps working meanwhile reads files the agent is still writing, or hands back
before the answer exists (rerun 3's judge returned UNKNOWN while its finders had all passed).
The rule lives here, not in each agent's text, because a hook reaches every caller of this
plugin's agents, including one that reads none of the plugin's files.
"""
import json
import sys

try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
if data.get("tool_name") not in ("Agent", "Task"):
    sys.exit(0)
# A plugin hook fires in the whole session; only spawns of or by this plugin's agents wait here.
spawned = (data.get("tool_input") or {}).get("subagent_type") or ""
if not (spawned.startswith("geovane:") or (data.get("agent_type") or "").startswith("geovane:")):
    sys.exit(0)

response = data.get("tool_response")
# A foreground spawn returns once the agent has ended, with status "completed".
if isinstance(response, dict) and response.get("status") == "completed":
    sys.exit(0)
text = json.dumps(response) if not isinstance(response, str) else response
# In the main session the spawn returns status "async_launched"; in a subagent or a -p run its
# text says the report "was delivered to you as a message". Both mean the answer comes later.
launched = isinstance(response, dict) and response.get("status") == "async_launched"
if not launched and "delivered to you as a message" not in text:
    sys.exit(0)

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": (
            "That agent runs in the background; its answer arrives later as a message. "
            "Start any other agent this step needs now, then stop and wait. In a subagent, stopping while an "
            "agent still runs is not handing back: each answer wakes you, and you answer after the last one. "
            "Until every answer arrives, do not read or write the files you gave the agents, "
            "and do not hand back or answer from what you have."
        ),
    }
}))
