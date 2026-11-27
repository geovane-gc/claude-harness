import json
import os
from collections import defaultdict
from datetime import datetime, timedelta

from . import events

NEVER_AUTO = {"decision", "deadline", "opinion", "people", "money", "prod", "suspicious", "review", "other", ""}
NEEDED_SENT = 20
NEEDED_RATIO = 0.9
WINDOW = 30
LOOKBACK_DAYS = 30


def decisions(days=LOOKBACK_DAYS):
    found = defaultdict(list)
    for offset in range(days, -1, -1):
        path = events.path_for((datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d"))
        if not os.path.exists(path):
            continue
        with open(path) as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if (event.get("kind") == "approval" and event.get("category")
                        and event.get("action") in ("sent", "discard", "edit", "stale")):
                    found[event["category"]].append(event)
    return found


def scoreboard():
    board = {}
    for category, history in decisions().items():
        recent = history[-WINDOW:]
        sent_high = [e for e in recent if e["action"] == "sent" and e.get("confidence") == "high"]
        discarded = [e for e in recent if e["action"] == "discard"]
        ratio = sum(e["action"] == "sent" for e in recent) / len(recent)
        board[category] = {"judged": len(recent), "sent_high": len(sent_high), "approved_ratio": round(ratio, 2),
                           "discarded": len(discarded),
                           "unlocked": (category not in NEVER_AUTO and len(sent_high) >= NEEDED_SENT
                                        and ratio >= NEEDED_RATIO and not discarded)}
    return board


def refresh(state):
    board = scoreboard()
    state["autonomy"] = {"board": board, "unlocked": sorted(c for c, b in board.items() if b["unlocked"]),
                         "at": datetime.now().strftime("%Y-%m-%d %H:%M")}
