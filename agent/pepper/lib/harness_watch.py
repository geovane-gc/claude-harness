import json
import subprocess
import time
from datetime import datetime, timedelta, timezone

from . import events, monitor
from .settings import CONFIG

# The harness repo the agent was installed from, and the folder of the agent template in it.
REPO = CONFIG.get("harness_repo", "")
PATH = CONFIG.get("harness_path", "agent")


def tick(state, env, log):
    if not REPO or time.time() - state.get("harness_checked", 0) < 6 * 3600:
        return
    state["harness_checked"] = time.time()
    since = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    done = subprocess.run([CONFIG["gh"], "api", f"repos/{REPO}/commits?path={PATH}&since={since}&per_page=50"],
                          capture_output=True, text=True, env=env, timeout=60)
    if done.returncode != 0:
        log(f"harness watch: {done.stderr.strip()[:200]}")
        return
    seen = set(state.setdefault("harness_commits_seen", []))
    for commit in json.loads(done.stdout or "[]"):
        sha, login = commit["sha"], ((commit.get("author") or {}).get("login") or commit["commit"]["author"]["name"])
        if sha in seen:
            continue
        seen.add(sha)
        if login != CONFIG["owner_github"]:
            monitor.root(state, f"harness:{sha[:7]}", f"⚠️ alguém mexeu no seu harness publicado: {login} — "
                                                      f"{commit['commit']['message'].splitlines()[0][:120]} "
                                                      f"https://github.com/{REPO}/commit/{sha} — leia antes de trazer.")
            events.record("harness_change", sha=sha, author=login)
    state["harness_commits_seen"] = sorted(seen)[-200:]
