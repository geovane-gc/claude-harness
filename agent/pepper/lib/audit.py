import json
import os
import subprocess
from datetime import datetime

from . import events, monitor, workdays
from .settings import CONFIG, OWNER

AREAS = ("code", "guards", "skills", "docs")
FRIDAY = 4
FROM_HOUR = 13
BACKLOG = os.path.expanduser("~/{{HOME_DIR_NAME}}/bin/backlog")
PAYLOADS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guard", "redteam_payloads.json")
KIND_OF = {"security": "develop", "bug": "develop", "risk": "develop", "cost": "improve", "simplify": "improve"}
MAX_FINDINGS = 8


def area_of(moment):
    return AREAS[moment.isocalendar()[1] % len(AREAS)]


def due(state, moment=None):
    moment = moment or datetime.now()
    week = moment.strftime("%G-W%V")
    return (moment.weekday() == FRIDAY and moment.hour >= FROM_HOUR and workdays.is_workday(moment)
            and state.get("audit_week") != week)


def plan(state, log):
    now = datetime.now()
    if not due(state, now):
        return
    state["audit_week"] = now.strftime("%G-W%V")
    area = area_of(now)
    state["talk_queue"].append({"kind": "audit", "question": None, "area": area,
                                "route": {"model": "opus", "effort": "high", "why": "weekly harness audit"},
                                "message": {"channel": CONFIG["control_channel_id"], "ts": f"{now.timestamp():.6f}",
                                            "thread_ts": "", "user": OWNER, "permalink": "", "text": ""}})
    log(f"talk queued: weekly audit of the {area} area")


def valid_payload(payload):
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("command"), str) and isinstance(payload.get("kind"), str):
        return "bash", {"kind": payload["kind"], "command": payload["command"][:2000]}
    if payload.get("tool") in ("Read", "Grep", "Glob") and isinstance(payload.get("input"), dict):
        return "read", {"kind": payload.get("kind", "bot"), "tool": payload["tool"], "input": payload["input"]}
    if isinstance(payload.get("message"), str):
        return "send", {"message": payload["message"][:2000]}
    return None


def keep_payloads(payloads, source):
    with open(PAYLOADS) as handle:
        corpus = json.load(handle)
    added = 0
    for payload in payloads or []:
        checked = valid_payload(payload)
        if checked and checked[1] not in corpus.setdefault(checked[0], []):
            corpus[checked[0]].append(dict(checked[1], source=source))
            added += 1
    if added:
        with open(PAYLOADS + ".tmp", "w") as handle:
            json.dump(corpus, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(PAYLOADS + ".tmp", PAYLOADS)
    return added


def settle(state, item, outcome, log):
    area, today = item.get("area", "?"), datetime.now().strftime("%d/%m")
    ids = []
    findings = [f for f in outcome.get("findings") or [] if isinstance(f, dict) and f.get("title")][:MAX_FINDINGS]
    for finding in findings:
        severity = finding.get("severity", "risk")
        title = f"[auditoria {area}{' · urgente' if severity == 'security' else ''}] {finding['title']}"[:200]
        ask = f"{finding.get('where', '')}: {finding.get('evidence', '')} -> {finding.get('fix', '')}"[:600]
        done = subprocess.run([BACKLOG, "add", KIND_OF.get(severity, "improve"), title, ask], capture_output=True,
                              text=True, timeout=60)
        if done.returncode == 0 and "#" in done.stdout:
            ids.append(done.stdout.split("#", 1)[1].split()[0])
    added = keep_payloads(outcome.get("payloads"), f"audit {area} {today}")
    events.record("audit", area=area, findings=len(findings), items=ids, payloads=added,
                  summary=outcome.get("summary", "")[:300])
    log(f"weekly audit ({area}): {len(findings)} finding(s) -> backlog {', '.join('#' + i for i in ids) or 'none'}; "
        f"{added} new red-team payload(s)")
    if any(f.get("severity") == "security" for f in findings):
        monitor.error(state, "audit", f"a auditoria de {area} achou {sum(f.get('severity') == 'security' for f in findings)} "
                                      f"ponto(s) de segurança: backlog {', '.join('#' + i for i in ids)}")
