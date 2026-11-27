#!/usr/bin/env python3
import json
import os
import re
import sys

AGENT_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
READ_ROOTS = [AGENT_HOME, "/tmp", "/private/tmp"]
OWN_TOOL_RESULTS = re.compile(r"^" + re.escape(os.path.expanduser("~/.claude/projects/")) + r"[^/]*{{HOME_DIR_NAME}}[^/]*/[^/]+/tool-results/[^/]+$")


def inside(path, roots):
    return any(path == root or path.startswith(root.rstrip("/") + "/") for root in roots)


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))


def check_write(event, directory):
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    import bash_guard
    bash_guard.STATE["kind"] = os.environ.get("PEPPER_RUN_KIND", "bot")
    if bash_guard.STATE["kind"] not in bash_guard.BUILD_KINDS:
        deny("Only build runs edit files.")
        return
    args = event.get("tool_input", {})
    path = args.get("file_path") or args.get("notebook_path") or ""
    try:
        bash_guard.writable(path, directory)
    except bash_guard.Refused as refused:
        deny(f"{refused}.")


def private_reach(event, directory):
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    import bash_guard
    if os.environ.get("PEPPER_RUN_KIND", "bot") not in bash_guard.OUTSIDE_FACING_KINDS:
        return None
    args = event.get("tool_input", {})
    tool = event.get("tool_name")
    target = args.get("file_path") or args.get("notebook_path") or args.get("path") or directory
    if tool == "Glob":
        target = os.path.join(args.get("path") or directory, re.split(r"[*?\[{]", args.get("pattern", ""), 1)[0] or ".")
    resolved = os.path.realpath(os.path.join(directory, os.path.expanduser(target)))
    if bash_guard.inside(resolved, bash_guard.PRIVATE):
        return f"{target} holds {{OWNER_FIRST_NAME}}'s private conversations or plans; a run that answers other people never reads it."
    if tool in ("Grep", "Glob") and bash_guard.private_below(resolved, directory):
        return (f"searching {target} reaches {{OWNER_FIRST_NAME}}'s private files (logs, state, backlog, memory); search knowledge/, "
                "pepper/skills or repos/<repo> instead.")
    return None


def main():
    event = json.load(sys.stdin)
    args = event.get("tool_input", {})
    directory = event.get("cwd") or os.getcwd()
    if event.get("tool_name") in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        check_write(event, directory)
        return
    reason = private_reach(event, directory)
    if reason:
        deny(reason)
        return
    for key in ("file_path", "path", "notebook_path"):
        value = args.get(key)
        if not value:
            continue
        resolved = os.path.realpath(os.path.join(directory, os.path.expanduser(value)))
        if OWN_TOOL_RESULTS.match(resolved):
            continue
        if not inside(resolved, READ_ROOTS):
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                     "permissionDecisionReason": f"{value} is outside what a run may "
                                                                                 "read (the agent folder and /tmp)."}}))
            return
    pattern = args.get("pattern", "")
    base = args.get("path") or directory
    prefix = re.split(r"[*?\[{]", pattern, 1)[0]
    if event.get("tool_name") == "Glob" and (".." in pattern.split("/") or not inside(
            os.path.realpath(os.path.join(base, os.path.expanduser(prefix or "."))), READ_ROOTS)):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": "Glob outside the agent folder and /tmp."}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as failure:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"{{AGENT_NAME}}'s guard failed ({failure}); "
                                                                             "refusing rather than letting it through."}}))
