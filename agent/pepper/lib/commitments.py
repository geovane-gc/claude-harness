import time
from datetime import datetime, timedelta

from . import approvals, events, monitor, morning, workdays
from .settings import CONFIG, OWNER, PREFIX, SLACK_URL

FROM_HOUR = 18
REMIND_WITHOUT_DUE_AFTER_DAYS = 2
TOOLS = ["mcp__claude_ai_Slack__slack_search_public_and_private", "mcp__claude_ai_Slack__slack_read_thread"]


def due(state, moment=None):
    moment = moment or datetime.now()
    return (workdays.is_workday(moment) and moment.hour >= FROM_HOUR
            and state.get("commitments_day") != moment.strftime("%Y-%m-%d"))


def plan(state, log):
    now = datetime.now()
    if not due(state, now):
        return
    state["commitments_day"] = now.strftime("%Y-%m-%d")
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    state["talk_queue"].append({"kind": "commitments", "question": None, "after": f"{start.timestamp():.0f}",
                                "message": {"channel": CONFIG["control_channel_id"], "ts": f"{now.timestamp():.6f}",
                                            "thread_ts": "", "user": OWNER, "permalink": "", "text": ""}})
    log("talk queued: today's commitments")


def settle(state, outcome, log):
    found = 0
    for item in outcome.get("commitments") or []:
        if not isinstance(item, dict) or not item.get("permalink", "").startswith(SLACK_URL):
            continue
        state.setdefault("commitments", {}).setdefault(item["permalink"], {
            "who": str(item.get("who", ""))[:80], "what": str(item.get("what", ""))[:200], "due": str(item.get("due", ""))[:10],
            "created": time.time(), "done": None})
        found += 1
    events.record("commitments", found=found)
    log(f"commitments: {found} found today")


def open_items(state):
    return {key: item for key, item in state.get("commitments", {}).items() if not item.get("done")}


def remind_now(item, today):
    if item.get("due"):
        return item["due"] <= today
    return time.time() - item["created"] > REMIND_WITHOUT_DUE_AFTER_DAYS * 86400


def tick(state, log):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    thread = morning.thread_ts(state)
    if not thread or state.get("commitments_reminded") == today or not workdays.is_workday(now):
        return 0
    state["commitments_reminded"] = today
    cost = 0
    for key, item in open_items(state).items():
        if not remind_now(item, today):
            continue
        late = " (atrasado)" if item.get("due") and item["due"] < today else ""
        when = f"até {datetime.strptime(item['due'], '%Y-%m-%d'):%d/%m}{late}" if item.get("due") else "sem prazo"
        _, spent = approvals.propose(state, "commitment", f"{PREFIX} 📌 prometido a {item['who']}: {item['what']} "
                                                          f"({when}) {key}\n✅ quando cumprir · ❌ não vale mais",
                                     thread, key=key)
        cost += spent
    return cost


def prune(state):
    cutoff = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    state["commitments"] = {key: item for key, item in state.get("commitments", {}).items()
                            if not item.get("done") or item["done"] >= cutoff}
