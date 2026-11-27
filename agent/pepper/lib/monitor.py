import re
import time
from datetime import datetime

from . import events, slack, workdays
from .settings import CONFIG, PREFIX, slack_link

ERROR_REPEAT_SECONDS = 3600


def channel():
    return CONFIG["control_channel_id"]


PR_REF = re.compile(r"[\w.-]+/[\w.-]+#\d+")


def ensure(state):
    for key, default in (("threads", {}), ("outbox", []), ("error_seen", {}), ("stats", {}), ("summary_day", ""),
                         ("topic_parent", {})):
        state.setdefault(key, default)
    for key, ts in sorted(state["threads"].items(), key=lambda pair: float(pair[1])):
        topic = topic_of(state, key)
        if topic != key:
            state["threads"].setdefault(topic, ts)


def topic_of(state, key):
    match = PR_REF.search(key)
    return f"pr:{match.group(0)}" if match else key


def link_topics(state, pr_ref, parent):
    state.setdefault("topic_parent", {})[f"pr:{pr_ref}"] = parent


def parent_of(state, key):
    return state.get("topic_parent", {}).get(topic_of(state, key), "")


def children_of(state, parent):
    return [topic.split(":", 1)[1] for topic, owner in state.get("topic_parent", {}).items() if owner == parent]


def summarize_to_parent(state, key, text):
    parent = parent_of(state, key)
    if parent:
        line = text.strip().splitlines()[0][:200]
        state["outbox"].append({"type": "reply", "key": parent,
                                "text": f"{PREFIX} ↳ {topic_of(state, key).split('/', 1)[1]}: {line}"})


def thread_of(state, key):
    return state["threads"].get(topic_of(state, key), "")


def stats(state):
    day = datetime.now().strftime("%Y-%m-%d")
    return state["stats"].setdefault(day, {"reviews": {}, "skipped": 0, "replies": 0, "errors": 0, "cost": 0.0})


def root(state, key, text):
    topic = topic_of(state, key)
    if topic in state["threads"] or any(i["type"] == "root" and i["key"] == topic for i in state["outbox"]):
        reply(state, topic, text)
        return
    state["outbox"].append({"type": "root", "key": topic, "text": f"{PREFIX} {text}"})
    summarize_to_parent(state, topic, text)


PHASES = {
    "building": "hammer_and_wrench", "pr_draft": "construction", "ci_red": "red_circle", "ci_rerun": "repeat",
    "ready": "eyes", "merged": "twisted_rightwards_arrows", "waiting_you": "raised_hand", "done": "white_check_mark",
    "blocked": "double_vertical_bar", "failed": "x", "reviewing": "hourglass_flowing_sand",
}


def phase(state, key, name):
    topics = [topic_of(state, key)]
    parent = parent_of(state, key)
    phases = state.setdefault("phases", {})
    if parent:
        siblings = [f"pr:{ref}" for ref in children_of(state, parent)]
        all_done = all((phases.get(t) or [""])[-1] == "done" or t == topics[0] for t in siblings)
        if name != "done" or all_done:
            topics.append(parent)
    for topic in topics:
        seen = state.setdefault("phases", {}).setdefault(topic, [])
        if seen and seen[-1] == name:
            continue
        seen.append(name)


def open_topic(state, key, header):
    topic = topic_of(state, key)
    if topic not in state["threads"] and not any(i["type"] == "root" and i["key"] == topic for i in state["outbox"]):
        parent = parent_of(state, topic)
        if parent and topic.startswith("pr:"):
            header = f"{header} · {parent.replace('backlog:', 'Backlog ')}"
        state["outbox"].append({"type": "root", "key": topic, "text": f"{PREFIX} {header}"})


def permalink(state, key):
    ts = thread_of(state, key)
    return slack_link(channel(), ts) if ts else ""


def reply(state, key, text, broadcast=False):
    item = {"type": "reply", "key": topic_of(state, key), "text": f"{PREFIX} {text}"}
    if broadcast:
        item["broadcast"] = True
    state["outbox"].append(item)
    summarize_to_parent(state, key, text)


def mark(state, key, emoji):
    state["outbox"].append({"type": "reaction", "key": topic_of(state, key), "emoji": emoji})


def review_started(state, ref, item):
    events.record("review_started", ref=ref, mode=item.get("mode", ""), permalink=item.get("permalink") or "")


def review_finished(state, ref, verdict):
    kind = verdict.get("verdict") or "failed"
    cost = verdict.get("cost") or 0
    events.record("review", ref=ref, verdict=kind, cost=round(cost, 4), url=verdict.get("review_url", ""),
                  model=(verdict.get("route") or {}).get("model", "opus"), rate=verdict.get("rate", {}),
                  mode=verdict.get("mode", ""), blocker=verdict.get("blocker_pt", ""), injection=bool(verdict.get("injection")))
    day = stats(state)
    day["reviews"][kind] = day["reviews"].get(kind, 0) + 1
    day["cost"] = round(day["cost"] + cost, 4)
    if kind == "failed":
        error(state, "review", f"{ref}: {verdict.get('reason') or 'no verdict'} — log {verdict.get('log', '')}")


def request_skipped(state, ref, reason, link):
    events.record("skip", ref=ref, reason=reason, permalink=link)
    stats(state)["skipped"] += 1


def error(state, kind, detail):
    stats(state)["errors"] += 1
    events.record("error", what=kind, detail=detail[:400])
    key = f"error:{kind}"
    last = state["error_seen"].get(kind, 0)
    if time.time() - last < ERROR_REPEAT_SECONDS:
        return
    state["error_seen"][kind] = time.time()
    if key not in state["threads"] and not any(i["type"] == "root" and i["key"] == key for i in state["outbox"]):
        root(state, key, f"⚠️ Erro: {kind}")
        mark(state, key, "warning")
    reply(state, key, f"{datetime.now():%d/%m %H:%M} {detail[:600]}")


def daily_review_due(state):
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    if now.hour < CONFIG["summary_hour"] or state["summary_day"] == today or not workdays.is_workday(now):
        return False
    state["summary_day"] = today
    return True


MAX_OUTBOX_ATTEMPTS = 4
THREADS_KEPT_SECONDS = 30 * 86400


def reopen_orphans(state):
    pending_roots = {i["key"] for i in state["outbox"] if i["type"] == "root"}
    for item in list(state["outbox"]):
        if item["type"] != "root" and item["key"] not in state["threads"] and item["key"] not in pending_roots:
            label = item["key"].split(":", 1)[-1]
            state["outbox"].insert(0, {"type": "root", "key": item["key"], "text": f"{PREFIX} 🔁 {label} (continuação)"})
            pending_roots.add(item["key"])


def outbox_calls(state):
    reopen_orphans(state)
    calls, items = [], []
    for item in state["outbox"]:
        if item["type"] == "root":
            calls.append(slack.send_call(channel(), "", item["text"]))
        elif item["key"] in state["threads"]:
            ts = state["threads"][item["key"]]
            calls.append(slack.send_call(channel(), ts, item["text"], item.get("broadcast", False))
                         if item["type"] == "reply" else slack.reaction_call(channel(), ts, item["emoji"]))
        else:
            continue
        items.append(item)
    return calls, items


def normalized(text):
    return re.sub(r"[\\\s`*_]", "", str(text or ""))[:160]


def same_call(call, result):
    if result["tool"] != call["tool"]:
        return False
    if result["args"] == call["args"]:
        return True
    wanted, got = call["args"], result["args"]
    if "message" not in wanted:
        return False
    keys = ("channel_id", "thread_ts", "message_ts", "timestamp", "emoji", "name")
    if any(str(wanted.get(k, "")) != str(got.get(k, "")) for k in keys if k in wanted or k in got):
        return False
    return normalized(wanted.get("message")) == normalized(got.get("message"))


def result_for(call, results):
    for result in results:
        if same_call(call, result):
            return result
    return None


def settle_outbox(state, calls, items, results):
    done = []
    for call, item in zip(calls, items):
        result = result_for(call, results)
        if result is None or (result["error"] and "already_reacted" not in result["text"]):
            continue
        if item["type"] == "root":
            ts = slack.sent_ts(result["text"])
            if ts:
                state["threads"][item["key"]] = ts
        done.append(item)
    for item in items:
        if item not in done:
            item["attempts"] = item.get("attempts", 0) + 1
    dropped = [i for i in state["outbox"] if i.get("attempts", 0) >= MAX_OUTBOX_ATTEMPTS]
    for item in dropped:
        events.record("outbox_dropped", key=item.get("key", ""), type=item["type"], text=item.get("text", "")[:200])
    state["outbox"] = [i for i in state["outbox"] if i not in done and i not in dropped]
    cutoff = time.time() - THREADS_KEPT_SECONDS
    state["threads"] = {k: v for k, v in state["threads"].items() if float(v) > cutoff}
