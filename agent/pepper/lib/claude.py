import json
import os
import subprocess

from .settings import CONFIG, clean_env

SLACK_TOOLS = "mcp__claude_ai_Slack__*"
GUARD_SETTINGS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guard", "settings.json")


def blocked_connectors(unblock=()):
    return [f"mcp__claude_ai_{name}__*" for name in CONFIG["other_connectors"] if name not in unblock]


def lean_command(prompt, model, skill_path, allowed, max_turns, disallowed=(), unblock=()):
    return [CONFIG["claude"], "-p", prompt, "--model", model, "--max-turns", str(max_turns),
            "--system-prompt-file", skill_path, "--setting-sources", "", "--disable-slash-commands",
            "--exclude-dynamic-system-prompt-sections", "--no-session-persistence",
            "--allowedTools", *allowed, "--disallowedTools", *blocked_connectors(unblock), *disallowed,
            "--settings", GUARD_SETTINGS, "--output-format", "stream-json", "--verbose"]


def tool_results(stream):
    calls, results, summary = {}, [], {}
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "assistant":
            for block in event["message"]["content"]:
                if block.get("type") == "tool_use":
                    calls[block["id"]] = (block["name"].split("__")[-1], block["input"])
        elif kind == "user":
            for block in event["message"].get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    content = block.get("content")
                    text = content if isinstance(content, str) else "".join(
                        part.get("text", "") for part in content or [])
                    name, args = calls.get(block.get("tool_use_id"), ("?", {}))
                    results.append({"tool": name, "args": args, "text": text,
                                    "error": bool(block.get("is_error"))})
        elif kind == "result":
            summary.update({"cost": event.get("total_cost_usd"), "turns": event.get("num_turns"),
                            "result": event.get("result"), "is_error": event.get("is_error")})
        elif kind == "rate_limit_event":
            info = event.get("rate_limit_info") or {}
            windows = info.get("unifiedWindows") or {}
            summary["rate"] = {"five_hour": (windows.get("five_hour") or {}).get("utilization"),
                               "seven_day": (windows.get("seven_day") or {}).get("utilization"),
                               "overage": bool(info.get("isUsingOverage")), "overage_allowed": info.get("overageStatus")}
        elif kind == "system" and event.get("subtype") == "init":
            listed = [s.get("status") for s in event.get("mcp_servers", []) if s.get("name") == "claude.ai Slack"]
            if listed:
                summary["slack_connected"] = "connected" in listed
    return results, summary


def run_tool_calls(calls, skill_path, timeout=300, approved=False):
    tools = sorted({"mcp__claude_ai_Slack__" + call["tool"] for call in calls})
    prompt = "Tools: " + ", ".join(tools) + "\nCalls:\n" + "\n".join(json.dumps(c, ensure_ascii=False) for c in calls)
    allowed = sorted({c["args"]["channel_id"] for c in calls if c["tool"] in ("slack_send_message", "slack_add_reaction")})
    env = clean_env({"PEPPER_ALLOWED_CHANNELS": ",".join(allowed) or CONFIG["control_channel_id"], "PEPPER_RUN_KIND": "calls",
                     **({"PEPPER_APPROVED_SEND": "1"} if approved else {})})
    done = subprocess.run(lean_command(prompt, CONFIG["scan_model"], skill_path, [SLACK_TOOLS], 4),
                          cwd="/tmp", env=env, capture_output=True, text=True, timeout=timeout)
    return tool_results(done.stdout)


def run_prompt(prompt, skill_path, model, timeout=180):
    env = clean_env({"PEPPER_RUN_KIND": "bot", "PEPPER_ALLOWED_CHANNELS": "none"})
    done = subprocess.run(lean_command(prompt, model, skill_path, ["Read"], 2, disallowed=[SLACK_TOOLS, "Bash", "Edit", "Write"]),
                          cwd="/tmp", env=env, capture_output=True, text=True, timeout=timeout)
    _, summary = tool_results(done.stdout)
    return (summary.get("result") or ""), summary
