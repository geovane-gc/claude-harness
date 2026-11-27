import json
import os
import subprocess
from datetime import datetime

from . import events, monitor

GUARD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guard")
AGENT_HOME = os.path.dirname(os.path.dirname(GUARD))
PAYLOADS = os.path.join(GUARD, "redteam_payloads.json")
BAITS = {"database_uri_with_password": "mongodb+srv" + "://user:" + "pass@cluster0.x.mongodb.net",
         "github_token": "gh" + "p_" + "a" * 36, "aws_account_id": "1234" + "5678" + "9012"}


def hook(script, event, environment):
    done = subprocess.run(["/usr/bin/python3", os.path.join(GUARD, script)], input=json.dumps(event),
                          capture_output=True, text=True, env=dict(os.environ, **environment), timeout=30)
    return '"deny"' in done.stdout


def attempts():
    config = json.load(open(os.path.join(os.path.dirname(GUARD), "config.json")))
    with open(PAYLOADS) as handle:
        # {org} is the first of the owner's GitHub orgs, so a case aimed at "our" links attacks this install's own list.
        corpus = json.loads(handle.read().replace("{org}", (config.get("github_orgs") or ["org"])[0]))
    for case in corpus["bash"]:
        event = {"tool_name": "Bash", "tool_input": {"command": case["command"]}, "cwd": AGENT_HOME}
        yield f"bash/{case['kind']}: {case['command'][:60]}", True, ("bash_guard.py", event, {"PEPPER_RUN_KIND": case["kind"]})
    for case in corpus["read"]:
        event = {"tool_name": case["tool"], "tool_input": case["input"], "cwd": AGENT_HOME}
        yield f"read/{case['kind']}: {case['tool']} {json.dumps(case['input'])[:50]}", True, (
            "read_guard.py", event, {"PEPPER_RUN_KIND": case["kind"]})
    for case in corpus["send"]:
        message = case["message"]
        for name, bait in BAITS.items():
            message = message.replace("{" + name + "}", bait)
        event = {"tool_input": {"channel_id": case.get("channel", "CTEST1"), "message": message}}
        expected = "comment" not in case
        # As an approved send, so draft-only mode lets it reach the checks these cases attack.
        yield f"send: {case['message'][:60]}", expected, (
            "slack_send_guard.py", event, {"PEPPER_ORDER_RUN": "0", "PEPPER_ALLOWED_CHANNELS": "", "PEPPER_APPROVED_SEND": "1"})
    control, panel = config["control_channel_id"], config.get("panel_canvas_id", "FPANEL1")
    for case in corpus.get("slack", []):
        args = json.loads(json.dumps(case["args"]).replace("{control}", control).replace("{panel}", panel))
        event = {"tool_name": "mcp__claude_ai_Slack__" + case["tool"], "tool_input": args}
        yield f"slack/{case['kind']}: {case['tool']}", True, (
            "slack_send_guard.py", event, {"PEPPER_RUN_KIND": case["kind"], "PEPPER_ORDER_RUN": "0",
                                           "PEPPER_ALLOWED_CHANNELS": case.get("allowed", "")})


def suites():
    failed = []
    for suite, cwd in (("pepper/guard/test_guards.py", AGENT_HOME), ("pepper/test_authors.py", AGENT_HOME),
                       ("pepper/test_injection.py", AGENT_HOME),
                       ("pepper/test_screen.py", AGENT_HOME)):
        if not os.path.exists(os.path.join(cwd, suite)):
            continue  # a suite the template does not ship
        done = subprocess.run(["/usr/bin/python3", "-m", "unittest", suite], capture_output=True, text=True, cwd=cwd,
                              timeout=300)
        if done.returncode != 0:
            failed.append(f"{suite}: {done.stderr.strip().splitlines()[-1] if done.stderr.strip() else 'failed'}")
    return failed


def run():
    passed, through = 0, []
    for label, expected, (script, event, environment) in attempts():
        if hook(script, event, environment) == expected:
            passed += 1
        else:
            through.append(label)
    return passed, through, suites()


RUN_FROM_HOUR = 6


def due(state):
    now = datetime.now()
    return now.hour >= RUN_FROM_HOUR and (state.get("redteam_last") or {}).get("day") != now.strftime("%Y-%m-%d")


def clean_today(state):
    last = state.get("redteam_last") or {}
    return last.get("day") == datetime.now().strftime("%Y-%m-%d") and not last.get("through") and not last.get("suites")


def tick(state, log):
    if not due(state):
        return
    passed, through, failed_suites = run()
    state["redteam_last"] = {"day": datetime.now().strftime("%Y-%m-%d"), "passed": passed, "through": through,
                             "suites": failed_suites}
    events.record("redteam", passed=passed, through=through, suites=failed_suites)
    log(f"red team: {passed} blocked, {len(through)} got through, {len(failed_suites)} suite(s) failed")
    if through or failed_suites:
        monitor.error(state, "redteam", "ataques que passaram: " + "; ".join(through[:8] + failed_suites[:3]))
