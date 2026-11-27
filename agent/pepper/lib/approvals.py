import json
import os
import re
import subprocess
import time
from datetime import datetime

from . import claude, events, github, monitor, slack
from .settings import CONFIG, OWNER, PREFIX, skill

APPROVE = {"white_check_mark", "heavy_check_mark", "ballot_box_with_check"}
DISCARD = {"x", "negative_squared_cross_mark", "no_entry_sign"}
EDIT = {"pencil2", "pencil", "memo"}
MAX_PENDING = 15
KEEP_SECONDS = 7 * 86400
REACTION_LINE = re.compile(r"^:([\w+\-']+): × \d+ — (.*)$", re.M)
AGENT_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ANSWERS = os.path.join(AGENT_HOME, "knowledge", "answers.md")
KNOWLEDGE_FILES = {"knowledge/answers.md", "knowledge/learned.md"}


def add(state, ts, kind, **data):
    state.setdefault("approvals", {})[ts] = dict(data, kind=kind, channel=data.get("channel") or CONFIG["control_channel_id"],
                                                 created=time.time())


def pending(state):
    return sorted(state.get("approvals", {}).items(), key=lambda kv: kv[1]["created"])[-MAX_PENDING:]


def calls(state):
    return [{"tool": "slack_get_reactions", "args": {"channel_id": item["channel"], "message_ts": ts}}
            for ts, item in pending(state)]


def unwrapped(text):
    try:
        answer = json.loads(text)
    except ValueError:
        return text
    return answer.get("result", text) if isinstance(answer, dict) else text


def reactions_of(text):
    text = unwrapped(text).replace("\\n", "\n")
    found = {}
    for emoji, people in REACTION_LINE.findall(text):
        found[emoji] = set(re.findall(r"\((U[A-Z0-9]+)\)", people))
    return found


def verdict(text):
    reacted = reactions_of(text)
    mine = {emoji for emoji, users in reacted.items() if OWNER in users}
    if mine & DISCARD:
        return "discard"
    if mine & APPROVE:
        return "approve"
    if mine & EDIT:
        return "edit"
    return None


def send(channel, thread_ts, text):
    # The owner approved this exact text with ✅: the one send that draft-only mode lets out.
    results, summary = claude.run_tool_calls([slack.send_call(channel, thread_ts, text)], skill("slack-fetch"), approved=True)
    ok = [r for r in results if r["tool"] == "slack_send_message" and not r["error"]]
    return (slack.sent_ts(ok[0]["text"]) if ok else None), summary.get("cost") or 0


def pr_facts(text, env):
    facts = {}
    for ref in github.pr_refs(text):
        try:
            status = github.pr_status(ref, env)
        except (github.TransientError, subprocess.TimeoutExpired):
            return None
        facts[ref] = {"state": status.get("state"), "head": status.get("headRefOid"), "error": status.get("error", "")}
    return facts


def send_draft(state, ts, item, log):
    facts = pr_facts(item["text"], github.gh_env())
    if facts is None:
        return False
    if facts != item.get("pr_facts", {}):
        monitor.reply(state, f"approval:{ts}", "↩️ não enviei: um PR citado mudou desde o rascunho. Responda na thread "
                                               "ou peça um rascunho novo.")
        events.record("approval", approval="draft", action="stale", ts=ts, category=item.get("category", ""))
        return True
    sent, _ = send(item["target_channel"], item["target_thread_ts"], item["text"])
    if not sent:
        return False
    state.get("questions", {}).pop(item.get("question_ts", ""), None)
    events.record("approval", approval="draft", action="sent", ts=ts, confidence=item.get("confidence", ""),
                  category=item.get("category", ""))
    log(f"approval {ts}: draft sent verbatim to {item['target_channel']}")
    return True


def keep_fact(state, ts, item, log):
    relative = item.get("file") if item.get("file") in KNOWLEDGE_FILES else "knowledge/answers.md"
    path = os.path.join(AGENT_HOME, relative)
    line = f"- {datetime.now():%Y-%m-%d} {item['fact']} ({item.get('source', '')})\n"
    with open(path, "a") as handle:
        handle.write(line)
    subprocess.run(["git", "-C", AGENT_HOME, "add", "--", path], capture_output=True, timeout=60)
    subprocess.run(["git", "-C", AGENT_HOME, "-c", "user.name=Claude", "-c", "user.email=claude@localhost", "commit", "-q",
                    "-m", "docs(knowledge): keep a fact {{OWNER_FIRST_NAME}} approved", "--", path], capture_output=True, timeout=60)
    events.record("approval", approval="fact", action="kept", ts=ts, file=relative, work=item.get("work", ""))
    log(f"approval {ts}: fact kept in {relative}")
    return True


def finish_commitment(state, ts, item, log):
    commitment = state.get("commitments", {}).get(item.get("key", ""))
    if commitment:
        commitment["done"] = datetime.now().strftime("%Y-%m-%d")
    log(f"approval {ts}: commitment done")
    events.record("approval", approval="commitment", action="done", ts=ts)
    return True


def apply_patch(state, ts, item, log):
    from . import patches
    return patches.apply(state, ts, item, log)


HANDLERS = {"draft": send_draft, "fact": keep_fact, "commitment": finish_commitment, "patch": apply_patch}


def settle(state, results, log):
    approvals = state.get("approvals", {})
    for result in results:
        if result["tool"] != "slack_get_reactions" or result["error"]:
            continue
        ts = result["args"].get("message_ts")
        item = approvals.get(ts)
        if not item:
            continue
        decided = verdict(result["text"])
        if decided == "approve" and HANDLERS[item["kind"]](state, ts, item, log):
            approvals.pop(ts, None)
        elif decided in ("discard", "edit"):
            approvals.pop(ts, None)
            if item["kind"] == "commitment" and decided == "discard":
                state.get("commitments", {}).get(item.get("key", ""), {})["done"] = "dropped"
            events.record("approval", approval=item["kind"], action=decided, ts=ts, confidence=item.get("confidence", ""),
                          category=item.get("category", ""))
    cutoff = time.time() - KEEP_SECONDS
    for ts in [ts for ts, item in approvals.items() if item["created"] < cutoff]:
        events.record("approval", approval=approvals[ts]["kind"], action="expired", ts=ts)
        approvals.pop(ts)


def propose(state, kind, text, thread_ts="", **data):
    sent, cost = send(CONFIG["control_channel_id"], thread_ts, text)
    if sent:
        add(state, sent, kind, **data)
        state.setdefault("threads", {}).setdefault(f"approval:{sent}", thread_ts or sent)
    return sent, cost
