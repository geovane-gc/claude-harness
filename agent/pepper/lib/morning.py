import json
import os
from datetime import datetime

from . import monitor, workdays
from .settings import CONFIG, STATE_DIR

OPENS_AT_HOUR = 7
POINTER = os.path.join(STATE_DIR, "morning.json")


def key(day=None):
    return f"morning:{day or datetime.now().strftime('%Y-%m-%d')}"


def thread_ts(state):
    return monitor.thread_of(state, key())


def tick(state, log):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if not workdays.is_workday(now) or now.hour < OPENS_AT_HOUR:
        return
    if state.get("morning_day") != today:
        state["morning_day"] = today
        if state.get("datadog_day") == today:
            return
        monitor.open_topic(state, key(), f"☀️ *Manhã {now:%d/%m}* — Datadog e lembretes na thread 👇")
        log("morning thread opened")
    ts = thread_ts(state)
    if ts:
        pointer = {"date": today, "channel": CONFIG["control_channel_id"], "thread_ts": ts}
        try:
            with open(POINTER) as handle:
                if json.load(handle) == pointer:
                    return
        except (OSError, ValueError):
            pass
        with open(POINTER + ".tmp", "w") as handle:
            json.dump(pointer, handle)
        os.replace(POINTER + ".tmp", POINTER)
