import os
import subprocess
from datetime import datetime

from . import events, morning, workdays
from .settings import CONFIG

REPOS = os.path.expanduser("~/{{HOME_DIR_NAME}}/repos")
# Which repos count as services and how Datadog names them come from config: a repo is watched when the owner committed
# to it recently, it is not in datadog_skip_repos, and datadog_service_names turns it into Datadog service names.
SKIP = set(CONFIG.get("datadog_skip_repos", [])) | {CONFIG.get("harness_repo", "").split("/")[-1]}
SERVICE_NAMES = CONFIG.get("datadog_service_names") or ["{repo}"]
ENVS = CONFIG.get("datadog_envs") or ["prod"]


def commits(repo, days):
    done = subprocess.run(["git", "-C", os.path.join(REPOS, repo), "log", "origin/HEAD", f"--since={days} days ago",
                           "--author={{OWNER_EMAIL}}", "--author={{OWNER_NAME}}", "--oneline"],
                          capture_output=True, text=True, timeout=60)
    return len(done.stdout.splitlines()) if done.returncode == 0 else 0


def services_today():
    ranked = []
    for repo in sorted(os.listdir(REPOS)) if os.path.isdir(REPOS) else []:
        if repo in SKIP or not os.path.isdir(os.path.join(REPOS, repo, ".git")):
            continue
        count = commits(repo, CONFIG["datadog_days_of_commits"])
        if count >= CONFIG["datadog_min_commits"]:
            ranked.append({"repo": repo, "commits": count, "envs": list(ENVS),
                           "services": [name.format(repo=repo) for name in SERVICE_NAMES]})
    return sorted(ranked, key=lambda r: -r["commits"])[:CONFIG["datadog_max_services"]]


def due(state):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if now.hour < CONFIG["datadog_hour"] or state.get("datadog_day") == today or not workdays.is_workday(now):
        return False
    state["datadog_day"] = today
    return True


def plan(state, log):
    if not CONFIG.get("datadog_watch", True):
        return
    if not morning.thread_ts(state):
        return
    if not due(state):
        return
    services = services_today()
    events.record("datadog_plan", services=[s["repo"] for s in services])
    state["talk_queue"].append({"kind": "datadog", "question": None, "services": services,
                                "morning_ts": morning.thread_ts(state), "message": {
        "channel": CONFIG["control_channel_id"], "ts": f"{datetime.now().timestamp():.6f}", "thread_ts": "",
        "user": CONFIG["owner_slack_id"], "permalink": "", "text": "datadog watch"}})
    log(f"talk queued: datadog watch on {', '.join(s['repo'] for s in services)}")
