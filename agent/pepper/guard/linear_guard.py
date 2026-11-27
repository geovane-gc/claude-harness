#!/usr/bin/env python3
"""Linear tools: reads in any run that lists them; save_issue and save_comment only in a run started by the owner's own
words in the control channel (PEPPER_ORDER_RUN=1). Deletes, merges, labels and every other write are refused."""
import json
import os
import sys

PEPPER = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, PEPPER)
from lib import linear  # noqa: E402


def reason(tool, order_run):
    if not tool.startswith(linear.PREFIX):
        return None
    name = tool[len(linear.PREFIX):]
    if name in linear.READ:
        return None
    if name in linear.WRITE:
        return None if order_run else (f"{name} changes Linear: only an order {{OWNER_FIRST_NAME}} wrote in "
                                       "#{{CONTROL_CHANNEL_NAME}} creates or changes a card. Ask him, with the card you would write.")
    return f"{name} is not a Linear tool {{AGENT_NAME}} uses (it reads cards and, on an order, saves an issue or a comment)."


def main():
    event = json.load(sys.stdin)
    refused = reason(event.get("tool_name", ""), os.environ.get("PEPPER_ORDER_RUN") == "1")
    if refused:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": refused}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as failure:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"{{AGENT_NAME}}'s Linear guard failed ({failure}); "
                                                                             "refusing rather than letting it through."}}))
