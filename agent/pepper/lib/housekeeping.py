import os
import time
from datetime import datetime, timedelta

from . import autonomy, commitments
from .settings import LOG_DIR, STATE_DIR

LOG_DAYS = 14
EVENT_DAYS = 90
STATS_DAYS = 30
WATCH_LOG_BYTES = 5 * 1024 * 1024


def due(state):
    return state.get("housekeeping_day") != datetime.now().strftime("%Y-%m-%d")


def old_files(folder, days, suffix):
    cutoff = time.time() - days * 86400
    if not os.path.isdir(folder):
        return []
    return [os.path.join(folder, name) for name in os.listdir(folder)
            if name.endswith(suffix) and os.path.getmtime(os.path.join(folder, name)) < cutoff]


def prune_state(state):
    cutoff = (datetime.now() - timedelta(days=STATS_DAYS)).strftime("%Y-%m-%d")
    state["stats"] = {day: value for day, value in state.get("stats", {}).items() if day >= cutoff}
    live = set(state.get("threads", {})) | {item.get("key") for item in state.get("outbox", [])}
    live |= {f"pr:{ref}" for ref in state.get("prs", {})}
    state["phases"] = {topic: value for topic, value in state.get("phases", {}).items() if topic in live}
    state["topic_parent"] = {child: parent for child, parent in state.get("topic_parent", {}).items()
                             if child in live or parent in live}
    hour_ago = time.time() - 3600
    state["author_runs"] = {user: [at for at in runs if at > hour_ago]
                            for user, runs in state.get("author_runs", {}).items() if any(at > hour_ago for at in runs)}
    week_ago = time.time() - 7 * 86400
    state["user_kinds"] = {user: kind for user, kind in state.get("user_kinds", {}).items() if kind.get("at", 0) > week_ago}
    state.pop("done", None)
    commitments.prune(state)
    autonomy.refresh(state)


def tick(state, log):
    if not due(state):
        return
    state["housekeeping_day"] = datetime.now().strftime("%Y-%m-%d")
    removed = old_files(LOG_DIR, LOG_DAYS, ".jsonl") + old_files(os.path.join(STATE_DIR, "events"), EVENT_DAYS, ".jsonl")
    for path in removed:
        os.remove(path)
    watch_log = os.path.join(LOG_DIR, "watch.log")
    if os.path.exists(watch_log) and os.path.getsize(watch_log) > WATCH_LOG_BYTES:
        os.replace(watch_log, watch_log + ".1")
    prune_state(state)
    log(f"housekeeping: removed {len(removed)} old log/event file(s), pruned state")
