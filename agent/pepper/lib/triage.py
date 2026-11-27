import json
import re

from . import claude, events
from .settings import CONFIG, skill

VERDICTS = {"ignore", "info", "knowledge", "action"}
CATEGORIES = {"fact", "status", "howto", "where", "review", "decision", "deadline", "opinion", "people", "money", "prod",
              "suspicious", "other", ""}
MAX_TEXT = 900
MAX_MESSAGES = 30


def key_of(message):
    return f"{message['channel']}:{message['ts']}"


def prompt(messages):
    blocks = []
    for message in messages[:MAX_MESSAGES]:
        text = message.get("text", "")[:MAX_TEXT].replace("</message>", "")
        where = message.get("channel_label", "") or message["channel"]
        sources = ",".join(message.get("sources", []))
        blocks.append(f'<message id="{key_of(message)}" where="{where}" how="{sources}" author="{message.get("user", "")}">\n'
                      f"{text}\n</message>")
    return "Classify these messages:\n" + "\n".join(blocks)


def parse(text, wanted):
    match = re.search(r"\{.*\}", text or "", re.S)
    try:
        items = json.loads(match.group(0)).get("items", []) if match else []
    except ValueError:
        items = []
    labels = {}
    for item in items:
        if not isinstance(item, dict) or item.get("id") not in wanted:
            continue
        verdict = item.get("verdict") if item.get("verdict") in VERDICTS else "action"
        category = item.get("category") if item.get("category") in CATEGORIES else "other"
        labels[item["id"]] = {"verdict": verdict, "category": category if verdict == "action" else "",
                              "confidence": "high" if item.get("confidence") == "high" else "low",
                              "why": str(item.get("why", ""))[:80]}
    for key in wanted:
        labels.setdefault(key, {"verdict": "action", "category": "other", "confidence": "low", "why": "not classified"})
    return labels


def classify(messages):
    if not messages:
        return {}, 0
    wanted = {key_of(m) for m in messages[:MAX_MESSAGES]}
    result, summary = claude.run_prompt(prompt(messages), skill("triage"), CONFIG["scan_model"])
    labels = parse(result, wanted)
    for message in messages[MAX_MESSAGES:]:
        labels[key_of(message)] = {"verdict": "action", "category": "other", "confidence": "low", "why": "over the batch"}
    return labels, summary.get("cost") or 0


def record(messages, labels):
    for message in messages:
        label = labels.get(key_of(message), {})
        events.record("triage", permalink=message.get("permalink", ""), author=message.get("user", ""), **label)
