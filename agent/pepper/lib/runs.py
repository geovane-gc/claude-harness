import json
import os
import re
import signal
import subprocess
import time

from . import claude
from .settings import log_file

START_SLACK_SECONDS = 120


def elapsed_seconds(pid):
    try:
        done = subprocess.run(["ps", "-o", "etime=", "-p", str(pid)], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = done.stdout.strip()
    if not text:
        return None
    days, _, clock = text.rpartition("-")
    parts = [int(p) for p in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return int(days or 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def alive(pid, started=None):
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    if started is None:
        return True
    elapsed = elapsed_seconds(pid)
    return elapsed is not None and elapsed + START_SLACK_SECONDS >= time.time() - started


KILL_AFTER_SECONDS = 600


def stop(pid, started, limit, log, label):
    overdue = time.time() - started - limit
    try:
        os.killpg(pid, signal.SIGKILL if overdue > KILL_AFTER_SECONDS else signal.SIGTERM)
        log(f"{label} {'killed' if overdue > KILL_AFTER_SECONDS else 'asked to stop'} after its time limit")
    except (ProcessLookupError, PermissionError):
        pass


def final_json(path):
    try:
        with log_file(path) as handle:
            results, summary = claude.tool_results(handle.read())
    except OSError:
        return [], {}, {}
    match = re.search(r"\{.*\}", (summary.get("result") or "").strip(), re.S)
    try:
        answer = json.loads(match.group(0)) if match else {}
    except ValueError:
        answer = {}
    return results, summary, answer
