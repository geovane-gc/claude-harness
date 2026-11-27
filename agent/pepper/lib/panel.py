import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime

from . import claude, events, monitor
from .settings import CONFIG, SLACK_URL, skill, slack_link

BACKLOG = os.path.expanduser("~/{{HOME_DIR_NAME}}/bin/backlog")
PHASE_PT = {"building": "build rodando", "pr_draft": "PR draft", "ci_red": "CI vermelho", "ci_rerun": "CI rodando de novo",
            "ready": "em review", "merged": "mergeado", "waiting_you": "esperando você", "done": "concluído",
            "blocked": "parado (ver thread)", "failed": "falhou"}
QUESTION_PT = {"daily review proposals": "Revisão do dia: próximos passos", "datadog findings": "Datadog: achados"}


def short(ref):
    return ref.split("/", 1)[1]


def link(text, url):
    return f"[{text}]({url})" if url else text


def paused(ref):
    repo = short(ref).split("#")[0] if "/" in ref else ref.split("#")[0]
    return repo in CONFIG.get("no_fix_repos", [])


def question_line(state, ts, record):
    url = slack_link(monitor.channel(), ts)
    origin = record.get("origin_text", "")
    readable = re.sub(r"<https?://[^>]*>|https?://\S+", "", origin).strip()
    title = (QUESTION_PT.get(origin) or readable or record.get("asked") or "pergunta")[:90]
    when = datetime.fromtimestamp(float(ts)).strftime("%d/%m %H:%M")
    return f"- {link(title, url)} — desde {when}"


def backlog_items():
    done = subprocess.run([BACKLOG, "list", "all"], capture_output=True, text=True, timeout=60)
    items = []
    for line in done.stdout.splitlines():
        match = re.match(r"#(\d+) \[(.)\] \((\w+)\) (.+?) — ", line)
        if match:
            items.append({"id": match.group(1), "mark": match.group(2), "title": match.group(4)[:80], "line": line})
    return items


def pr_phase(state, ref):
    phases = state.get("phases", {}).get(f"pr:{ref}") or []
    return phases[-1] if phases else ""


FINISHED = {"mergeado", "fechado", "concluído"}


def child_status(state, ref):
    info = state.get("prs", {}).get(ref) or {}
    view = info.get("view") or {}
    if info.get("merged"):
        return "mergeado"
    if info.get("closed_seen"):
        return "fechado"
    if info.get("needs_you"):
        return "esperando você"
    if view.get("check") == "red":
        return "CI vermelho"
    if view.get("draft"):
        return "PR draft"
    return "em review"


def open_children(state, children):
    return [ref for ref in children if child_status(state, ref) not in FINISHED]


BACKLOG_REF = re.compile(r"(?:backlog\s*)?#(\d+)\b", re.I)


def settled_by_backlog(record, closed):
    asked = record.get("asked", "")
    ids = set(BACKLOG_REF.findall(asked)) if "backlog" in asked.lower() else set()
    return bool(ids) and ids <= closed


def waiting(state):
    items = backlog_items()
    closed = {item["id"] for item in items if item["mark"] in ("x", "-")}
    for ts in [ts for ts, record in state.get("questions", {}).items() if settled_by_backlog(record, closed)]:
        state["questions"].pop(ts, None)
    lines = [question_line(state, ts, record) for ts, record in sorted(state.get("questions", {}).items())]
    for item in items:
        if item["mark"] == "s":
            title, topic = f"Backlog #{item['id']} {item['title']}", "backlog:#" + item["id"]
            lines.append(f"- {link(title, monitor.permalink(state, topic))} — precisa de uma sessão contigo")
    for ref, info in state.get("prs", {}).items():
        view = info.get("view") or {}
        if not view or info.get("closed_seen") or not info.get("needs_you") or paused(ref):
            continue
        lines.append(f"- {link(short(ref), monitor.permalink(state, ref) or view['url'])} — {info['needs_you'][:160]}")
    return lines


def in_progress(state, items):
    lines = []
    for item in items:
        topic = f"backlog:#{item['id']}"
        all_children = monitor.children_of(state, topic)
        children = [ref for ref in all_children if not paused(ref)]
        if all_children and not children:
            continue
        if item["mark"] not in "~>" and not open_children(state, children):
            continue
        if children:
            counts = {}
            for ref in children:
                label = child_status(state, ref)
                label = "contigo (acima)" if label.startswith("esperando") else label
                counts[label] = counts.get(label, 0) + 1
            status = f"{len(children)} PR{'s' if len(children) > 1 else ''}: " + ", ".join(f"{n} {label}" for label, n in counts.items())
        else:
            status = "build rodando" if item["mark"] == "~" else "na fila do build"
        title = f"Backlog #{item['id']} {item['title']}"
        source = re.search(r"src (" + re.escape(SLACK_URL) + r"archives/" + monitor.channel() + r"/\S+)", item.get("line", ""))
        lines.append(f"- {link(title, monitor.permalink(state, topic) or (source.group(1) if source else ''))} — {status}")
    for ref, info in state.get("prs", {}).items():
        view = info.get("view") or {}
        if (not view or info.get("closed_seen") or info.get("needs_you") or paused(ref)
                or monitor.parent_of(state, f"pr:{ref}")):
            continue
        status = "draft" if view.get("draft") else ("aprovado" if view.get("decision") == "APPROVED" else "em review")
        if ref in state.get("prfix_running", []) or (view.get("check") == "red" and info.get("fix_head")):
            status += ", {{AGENT_NAME}} corrigindo o CI"
        elif view.get("check") == "pending":
            status += ", CI rodando"
        lines.append(f"- {link(short(ref), monitor.permalink(state, ref) or view['url'])} — {view.get('title', '')[:70]} ({status})")
    return lines


def done_today(state, items):
    path = events.path_for()
    merged, reviews, cost = [], {}, 0.0
    if os.path.exists(path):
        for line in open(path):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("kind") == "pr_minder" and event.get("action") == "merged" and not paused(event["ref"]):
                merged.append(event["ref"].split("/", 1)[1])
            if event.get("kind") == "review":
                reviews[event.get("verdict", "?")] = reviews.get(event.get("verdict", "?"), 0) + 1
            cost += float(event.get("cost") or 0)
    today = datetime.now().strftime("%Y-%m-%d")
    delivered = [f"#{i['id']}" for i in items if i["mark"] == "x" and f"done {today}" in i["line"]
                 and not open_children(state, monitor.children_of(state, f"backlog:#{i['id']}"))]
    lines = []
    if merged:
        lines.append(f"- Mergeados: {', '.join(merged)}")
    if delivered:
        lines.append(f"- Backlog entregue: {', '.join(delivered)}")
    if reviews:
        total = sum(reviews.values())
        lines.append(f"- Reviews: {total} ({reviews.get('approved', 0)} aprovados, "
                     f"{reviews.get('changes_requested', 0)} com mudanças) — detalhes na revisão das 19h")
    lines.append(f"- Custo do {{AGENT_NAME}} hoje: ${cost:.2f} (equivalente de API, dentro do plano; atualizado de hora em hora)")
    return lines


HEALTH_NAMES = {"slack": "Slack", "pr_minder": "PRs", "reviews": "reviews", "talks": "conversas",
                "harness_watch": "harness", "redteam": "red team", "morning": "manhã", "panel": "painel",
                "commitments": "compromissos", "housekeeping": "manutenção"}
FAILED_RECENTLY_SECONDS = 3600


def moment(timestamp, now=None):
    when, today = datetime.fromtimestamp(timestamp), datetime.fromtimestamp(now or time.time()).date()
    if when.date() == today:
        return f"{when:%H:%M}"
    if (today - when.date()).days == 1:
        return f"ontem {when:%H:%M}"
    return f"{when:%d/%m %H:%M}"


def health(state):
    entries = state.get("health", {})
    now = time.time()
    failing = [(name, entry) for name, entry in entries.items()
               if entry.get("failed", 0) > entry.get("ok", 0) and now - entry["failed"] < FAILED_RECENTLY_SECONDS]
    last = max([entry.get("ok", 0) for entry in entries.values()] or [0])
    if not failing:
        return [f"- tudo ok; última passada {datetime.fromtimestamp(last):%H:%M}" if last else "- sem passada registrada"]
    lines = []
    for name, entry in sorted(failing):
        since = f"; último ok {moment(entry['ok'])}" if entry.get("ok") else ""
        lines.append(f"- :warning: {HEALTH_NAMES.get(name, name)}: falhou {moment(entry['failed'])}"
                     f" ({entry.get('error', '')[:90]}){since}")
    return lines


def commitment_lines(state):
    lines = []
    for key, item in sorted(state.get("commitments", {}).items(), key=lambda kv: kv[1].get("due") or "9999"):
        if item.get("done"):
            continue
        when = f"até {item['due'][8:10]}/{item['due'][5:7]}" if item.get("due") else "sem prazo"
        lines.append(f"- {link(item['who'] + ': ' + item['what'][:80], key)} — {when}")
    return lines


def approval_lines(state):
    lines = []
    for ts, item in state.get("approvals", {}).items():
        url = slack_link(item["channel"], ts)
        if item["kind"] == "fact":
            lines.append(f"- {link('Guardar no knowledge: ' + item.get('fact', '')[:70], url)} — ✅ ou ❌")
        elif item["kind"] == "patch":
            where = item.get("ref", "").split("/", 1)[-1] or "{{AGENT_NAME}}"
            lines.append(f"- {link('Patch protegido em ' + where + ': ' + item.get('summary', '')[:60], url)} — ✅ aplico ou ❌")
    return lines


def render(state):
    items = backlog_items()
    sections = [("## :raised_hand: Esperando você", (waiting(state) + approval_lines(state)) or ["- nada agora"]),
                ("## :pushpin: Teus compromissos", commitment_lines(state) or ["- nenhum aberto"]),
                ("## :hammer_and_wrench: Em andamento", in_progress(state, items) or ["- nada agora"]),
                ("## :stethoscope: Saúde", health(state)),
                ("## :white_check_mark: Feito hoje", done_today(state, items))]
    body = "\n\n".join(f"{title}\n\n" + "\n".join(lines) for title, lines in sections)
    return body


def tick(state, log):
    canvas = CONFIG.get("panel_canvas_id")
    if not canvas:
        return 0
    body = render(state)
    hour = datetime.now().strftime("%Y-%m-%d %H")
    stable = re.sub(r"Custo do {{AGENT_NAME}} hoje: \$[\d.]+", "", body)
    digest = hashlib.sha1(stable.encode()).hexdigest()
    if digest == state.get("panel_digest") and state.get("panel_hour") == hour:
        return 0
    content = f"{body}\n\n_atualizado {datetime.now():%d/%m %H:%M}_"
    sections = state.get("panel_sections") or []
    if not sections:
        read = {"tool": "slack_read_canvas", "args": {"canvas_id": canvas}}
        results, summary = claude.run_tool_calls([read], skill("slack-fetch"))
        mapping = parse_mapping(results)
        sections = [sid for sid, text in mapping.items() if not text.startswith("# ")]
    if not sections:
        log("panel: canvas has no body section to replace")
        return 0
    ops = [{"edit_type": "replace", "section_id": sections[0], "content": content}]
    ops += [{"edit_type": "delete", "section_id": sid} for sid in sections[1:]]
    call = {"tool": "slack_update_canvas", "args": {"canvas_id": canvas, "sections": ops}}
    results, summary = claude.run_tool_calls([call], skill("slack-fetch"))
    mapping = parse_mapping(results)
    if not mapping:
        state["panel_sections"] = []
        log(f"panel: update failed {json.dumps([r['text'][:200] for r in results])}")
        return summary.get("cost") or 0
    state["panel_sections"] = [sid for sid, text in mapping.items() if not text.startswith("# ")]
    state["panel_digest"] = digest
    state["panel_hour"] = hour
    log("panel: canvas updated")
    return summary.get("cost") or 0


def parse_mapping(results):
    for result in results:
        if result["error"]:
            continue
        try:
            data = json.loads(result["text"])
            data = json.loads(data["result"]) if isinstance(data.get("result"), str) else data
        except (ValueError, KeyError, TypeError):
            match = re.search(r'"section_id_mapping"\s*:\s*(\{.*?\})', result["text"], re.S)
            data = {"section_id_mapping": json.loads(match.group(1))} if match else {}
        mapping = data.get("section_id_mapping") or {}
        if mapping:
            return mapping
    return {}
