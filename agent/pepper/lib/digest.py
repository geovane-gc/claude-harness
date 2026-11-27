import json
import os
from collections import Counter, defaultdict
from datetime import datetime

from datetime import timedelta

from . import events, panel, workdays

MAX_LIST = 25


def day_events(day=None):
    path = events.inside_events(events.path_for(day))
    if not os.path.exists(path):
        return []
    found = []
    with open(path) as handle:
        for line in handle:
            try:
                found.append(json.loads(line))
            except ValueError:
                continue
    return found


def review_days(today=None):
    today = today or datetime.now().date()
    previous = workdays.previous_workday(today)
    return [(previous + timedelta(days=n)).isoformat() for n in range(1, (today - previous).days + 1)]


def build(state, days=None):
    days = days or [datetime.now().strftime("%Y-%m-%d")]
    found = [event for day in days for event in day_events(day)]
    by_kind = Counter(e.get("kind") for e in found)
    cost = defaultdict(float)
    for event in found:
        cost[event.get("kind", "?") if event.get("kind") != "talk" else f"talk:{event.get('type', '?')}"] += float(event.get("cost") or 0)
    reviews = [e for e in found if e.get("kind") == "review"]
    talks = [e for e in found if e.get("kind") == "talk"]
    passes = [e for e in found if e.get("kind") == "pass"]
    return {
        "days": days,
        "passes": len(passes),
        "messages_read": sum(e.get("fetched", 0) for e in passes),
        "requests": sum(e.get("requests", 0) for e in passes),
        "external_ignored": sum(e.get("external_ignored", 0) for e in passes),
        "incomplete_passes": sum(1 for e in passes if e.get("complete") is False),
        "reviews": dict(Counter(e.get("verdict", "?") for e in reviews)),
        "changes_requested": [{"ref": e.get("ref"), "blocker": (e.get("blocker") or "")[:200], "url": e.get("url")}
                              for e in reviews if e.get("verdict") == "changes_requested"][:MAX_LIST],
        "slowest_reviews": sorted(({"ref": e.get("ref"), "cost": e.get("cost")} for e in reviews),
                                  key=lambda r: -(r["cost"] or 0))[:3],
        "skips": dict(Counter((e.get("reason") or "?")[:60] for e in found if e.get("kind") == "skip")),
        "talks": {kind: dict(Counter(e.get("action") for e in talks if e.get("type") == kind))
                  for kind in sorted({e.get("type") for e in talks})},
        "talk_summaries": [{"type": e.get("type"), "action": e.get("action"), "permalink": e.get("permalink"),
                            "summary": (e.get("summary") or "")[:200]} for e in talks
                           if e.get("type") not in ("bot", "person") and e.get("action") != "ignored"][:MAX_LIST],
        "pr_minder": dict(Counter(e.get("action") for e in found if e.get("kind") == "pr_minder")),
        "errors": [{"at": e.get("at"), "kind": e.get("what") or e.get("step") or e.get("type"),
                    "text": (e.get("detail") or e.get("text") or e.get("error") or "")[:200]}
                   for e in found if e.get("kind") in ("error", "step_failed", "outbox_dropped")][:MAX_LIST],
        "security": {"injection_scans_hit": [e.get("ref") for e in found if e.get("kind") == "injection"],
                     "guests_ignored": sum(1 for e in talks if e.get("type") == "guest"),
                     "author_limit_hits": sum(1 for e in talks if e.get("type") == "author_limit")},
        "audit": [{"area": e.get("area"), "findings": e.get("findings"), "backlog_items": e.get("items"),
                   "summary": e.get("summary")} for e in found if e.get("kind") == "audit"],
        "redteam": [{"blocked": e.get("passed"), "through": e.get("through"), "suites": e.get("suites")}
                    for e in found if e.get("kind") == "redteam"][-1:],
        "triage": dict(Counter(e.get("verdict", "?") for e in found if e.get("kind") == "triage")),
        "knowledge": {"kept": [e.get("file", "") for e in found if e.get("kind") == "approval" and e.get("action") == "kept"],
                      "work_from_facts": [w for e in found if e.get("kind") == "knowledge" for w in e.get("work", [])]
                      + [e.get("work") for e in found if e.get("kind") == "approval" and e.get("action") == "kept" and e.get("work")]},
        "drafts": dict(Counter(e.get("action", "?") for e in found if e.get("kind") == "approval" and e.get("category"))),
        "autonomy": (state.get("autonomy") or {}).get("board", {}),
        "cost_by_kind": {kind: round(value, 4) for kind, value in sorted(cost.items(), key=lambda kv: -kv[1]) if value},
        "cost_total": round(sum(cost.values()), 4),
        "waiting_for_owner": panel.waiting(state),
        "event_counts": dict(by_kind),
    }
