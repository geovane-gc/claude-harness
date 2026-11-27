import time
from datetime import datetime

from . import approvals, events, workdays
from .settings import CONFIG, OWNER, PREFIX, SLACK_URL

FROM_HOUR = 18
TOOLS = ["mcp__claude_ai_Slack__slack_search_public_and_private", "mcp__claude_ai_Slack__slack_read_thread",
         "Read", "Grep", "Glob"]
LEARNED = "knowledge/learned.md"
MAX_FACTS = 8


def due(state, moment=None):
    moment = moment or datetime.now()
    return (workdays.is_workday(moment) and moment.hour >= FROM_HOUR
            and state.get("knowledge_day") != moment.strftime("%Y-%m-%d"))


def plan(state, log):
    now = datetime.now()
    if not due(state, now):
        return
    state["knowledge_day"] = now.strftime("%Y-%m-%d")
    inbox, state["knowledge_inbox"] = state.get("knowledge_inbox", []), []
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    state["talk_queue"].append({"kind": "knowledge", "question": None, "after": f"{start.timestamp():.0f}",
                                "inbox": [i["permalink"] for i in inbox][-30:],
                                "message": {"channel": CONFIG["control_channel_id"], "ts": f"{now.timestamp():.6f}",
                                            "thread_ts": "", "user": OWNER, "permalink": "", "text": ""}})
    log(f"talk queued: today's knowledge ({len(inbox)} flagged message(s))")


def prompt(item):
    flagged = "\n".join(f"- {link}" for link in item.get("inbox", [])) or "- (none)"
    return (f"Today is {datetime.now():%Y-%m-%d (%A)}. Collect today's durable facts. Today started at timestamp "
            f"{item['after']}. Messages flagged as knowledge during the day:\n{flagged}")


def settle(state, outcome, log):
    facts = [f for f in outcome.get("facts") or [] if isinstance(f, dict) and f.get("fact")
             and str(f.get("source", "")).startswith(SLACK_URL)][:MAX_FACTS]
    events.record("knowledge", proposed=len(facts),
                  work=[f.get("work", "")[:160] for f in facts if f.get("work")])
    if not facts:
        log("knowledge: nothing durable today")
        return 0
    header, cost = approvals.send(CONFIG["control_channel_id"], "",
                                  f"{PREFIX} 📚 *Conhecimento de hoje*: {len(facts)} fato(s) das conversas em que você está. "
                                  f"✅ em cada um que eu devo guardar, ❌ no que não.")
    if not header:
        return cost
    for fact in facts:
        work = f"\n↳ trabalho: {fact['work'][:160]}" if fact.get("work") else ""
        _, spent = approvals.propose(state, "fact", f"{PREFIX} {fact['fact'][:400]} ({fact['source']}){work}\n✅ guardo · ❌ não",
                                     header, fact=fact["fact"][:400], source=fact["source"], file=LEARNED,
                                     work=fact.get("work", "")[:160])
        cost += spent
    log(f"knowledge: {len(facts)} fact(s) proposed")
    return cost
