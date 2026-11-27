import difflib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime

from . import approvals, claude, events, monitor, slack
from .settings import CONFIG, PREFIX, STATE_DIR, skill

AGENT_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATCH_ROOT = "/tmp/pepper-patch"
VALIDATE_ROOT = os.path.expanduser("~/Library/Caches/pepper-validate")
ALLOWED = re.compile(r"^(pepper/guard/[\w.-]+\.(py|json)|pepper/lib/[\w.-]+\.py|pepper/[\w.-]*test_[\w.-]+\.py|"
                     r"pepper/skills/[\w./-]+\.md|knowledge/security-policy\.md|plugin/hooks/[\w.-]+|bin/[\w.-]+)$")
SUITES = ["guard/test_guards.py"]
DIFF_LINES_SHOWN = 60
TEST_NAME = re.compile(r"^\s*def (test_\w+)\(", re.M)


class Rejected(Exception):
    pass


def contained(base, relative):
    root = os.path.realpath(base)
    path = os.path.realpath(os.path.join(root, str(relative)))
    if ".." in str(relative).split("/") or os.path.commonpath([root, path]) != root:
        raise Rejected(f"{relative} is outside {base}")
    return path


def read(base, relative):
    path = contained(base, relative)
    try:
        with open(path) as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def collect(patch):
    folder = os.path.realpath(str(patch.get("dir", "")))
    if not folder.startswith(os.path.realpath(PATCH_ROOT) + os.sep):
        raise Rejected(f"the patch folder must be under {PATCH_ROOT}")
    files = {}
    for relative in patch.get("files") or []:
        relative = str(relative).strip("/")
        if not ALLOWED.match(relative) or ".." in relative.split("/"):
            raise Rejected(f"{relative} is not a file a patch may change")
        content = read(folder, relative)
        if content is None:
            raise Rejected(f"{relative} is missing from the patch folder")
        files[relative] = content
    if not files:
        raise Rejected("the patch names no file")
    return files


def unified(files):
    lines = []
    for relative, new in files.items():
        old = read(AGENT_HOME, relative) or ""
        lines += difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{relative}", f"b/{relative}")
    return "".join(lines)


def tests_kept(files):
    for relative, new in files.items():
        old = read(AGENT_HOME, relative) or ""
        missing = set(TEST_NAME.findall(old)) - set(TEST_NAME.findall(new))
        if missing:
            raise Rejected(f"{relative} drops tests: {', '.join(sorted(missing))[:200]}")
        if "skip" in new and new.count("unittest.skip") > old.count("unittest.skip"):
            raise Rejected(f"{relative} adds a skip")


NESTED = "PEPPER_VALIDATING"


def run(args, cwd, timeout=600):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          env=dict(os.environ, **{NESTED: "1"}))


def validate(files):
    if os.environ.get(NESTED) == "1":
        raise Rejected("a validation cannot start another validation")
    tests_kept(files)
    os.makedirs(VALIDATE_ROOT, exist_ok=True)
    folder = os.path.join(VALIDATE_ROOT, f"{int(time.time() * 1000)}")
    added = run(["git", "-C", AGENT_HOME, "worktree", "add", "--detach", "-q", folder, "HEAD"], AGENT_HOME, 120)
    if added.returncode != 0:
        raise Rejected(f"could not prepare a copy: {added.stderr.strip()[:200]}")
    try:
        os.makedirs(os.path.join(folder, "pepper", "state", "skills"), exist_ok=True)
        for relative, content in files.items():
            target = contained(folder, relative)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as handle:
                handle.write(content)
        suites = SUITES + sorted(n for n in os.listdir(os.path.join(folder, "pepper"))
                                 if re.match(r"test_\w+\.py$", n) and n != "test_patches.py")
        for suite in suites:
            done = run(["/usr/bin/python3", "-m", "unittest", suite], os.path.join(folder, "pepper"))
            if done.returncode != 0:
                lines = [l for l in (done.stderr + "\n" + done.stdout).splitlines() if l.strip()]
                detail = [l for l in lines if l.startswith(("FAIL:", "ERROR:", "AssertionError", "Traceback"))][:4] or lines[-4:]
                raise Rejected(f"{suite} fails with the patch (exit {done.returncode}): {' | '.join(detail)[:400] or 'no output'}")
        red = run(["/usr/bin/python3", "-I", "-c", "import sys,os; sys.path.insert(0,os.getcwd()); from lib import redteam; "
                   "p,t,f=redteam.run(); print(len(t)+len(f))"], os.path.join(folder, "pepper"))
        if red.returncode != 0 or red.stdout.strip().splitlines()[-1:] != ["0"]:
            raise Rejected(f"the red team does not pass with the patch: {(red.stdout + red.stderr).strip()[-300:]}")
        return len(suites)
    finally:
        run(["git", "-C", AGENT_HOME, "worktree", "remove", "--force", folder], AGENT_HOME, 120)


def save(patch_id, files, diff):
    folder = os.path.join(STATE_DIR, "patches", patch_id)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "patch.json"), "w") as handle:
        json.dump(files, handle)
    with open(os.path.join(folder, "patch.diff"), "w") as handle:
        handle.write(diff)
    with open(os.path.join(folder, "base.json"), "w") as handle:
        json.dump({relative: read(AGENT_HOME, relative) or "" for relative in files}, handle)
    return folder


def rebased(files, base):
    merged = {}
    scratch = tempfile.mkdtemp(prefix="pepper-rebase-")
    try:
        for relative, theirs in files.items():
            ours = read(AGENT_HOME, relative) or ""
            if relative not in base or ours == base[relative]:
                merged[relative] = theirs
                continue
            paths = []
            for name, content in (("ours", ours), ("base", base[relative]), ("theirs", theirs)):
                paths.append(os.path.join(scratch, name))
                with open(paths[-1], "w") as handle:
                    handle.write(content)
            done = run(["git", "merge-file", "-p", *paths], scratch, 60)
            if done.returncode != 0:
                raise Rejected(f"{relative} mudou depois da proposta e o merge tem conflito: preciso de um patch novo")
            merged[relative] = done.stdout
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return merged


def submit(state, item, outcome, log):
    patch = outcome.get("protected_patch")
    if not isinstance(patch, dict):
        return
    topic = f"pr:{item['ref']}" if item.get("ref") else f"backlog:#{item.get('backlog_id', '')}"
    try:
        files = collect(patch)
        diff = unified(files)
        if not diff:
            raise Rejected("the patch changes nothing")
        suites = validate(files)
    except (Rejected, subprocess.TimeoutExpired, OSError) as failure:
        monitor.reply(state, topic, f"⛔ patch em arquivo protegido descartado antes de chegar a você: {failure}")
        events.record("patch", action="rejected", reason=str(failure)[:300])
        log(f"protected patch rejected: {failure}")
        return
    patch_id = f"{datetime.now():%Y%m%d-%H%M%S}"
    for old_ts, old in list(state.get("approvals", {}).items()):
        if old["kind"] == "patch" and old.get("topic") == topic:
            state["approvals"].pop(old_ts)
            events.record("patch", action="superseded", id=old.get("patch_id"), by=patch_id)
    folder = save(patch_id, files, diff)
    shown = diff.splitlines()[:DIFF_LINES_SHOWN]
    more = "" if len(diff.splitlines()) <= DIFF_LINES_SHOWN else f"\n… diff completo em {folder}/patch.diff"
    text = (f"{PREFIX} 🔐 Patch em arquivo protegido, pronto e validado numa cópia isolada ({suites} suítes e o red team "
            f"passaram, nenhum teste removido): {str(patch.get('summary', ''))[:300]}\nArquivos: {', '.join(files)}\n"
            f"```\n" + "\n".join(shown)[:2600] + f"\n```{more}\n✅ aplico · ❌ descarto")
    thread = state.get("threads", {}).get(topic, "")
    sent, _ = approvals.propose(state, "patch", text, thread, patch_id=patch_id, topic=topic, ref=item.get("ref", ""),
                                summary=str(patch.get("summary", ""))[:300],
                                threads=[t for t in outcome.get("threads_done") or [] if isinstance(t, str)][:10],
                                rerequest=[r for r in outcome.get("rerequest") or [] if isinstance(r, str)][:5],
                                reply=str(outcome.get("reply") or "")[:4000])
    events.record("patch", action="proposed" if sent else "unsent", id=patch_id, files=list(files))
    log(f"protected patch {patch_id} validated and proposed: {list(files)}")


def apply(state, ts, item, log):
    folder = os.path.join(STATE_DIR, "patches", item["patch_id"])
    try:
        with open(contained(os.path.join(STATE_DIR, "patches"), os.path.join(item["patch_id"], "patch.json"))) as handle:
            files = json.load(handle)
        base_path = contained(os.path.join(STATE_DIR, "patches"), os.path.join(item["patch_id"], "base.json"))
        if os.path.exists(base_path):
            with open(base_path) as handle:
                files = rebased(files, json.load(handle))
        tests_kept(files)
        validate(files)
    except (Rejected, OSError, ValueError, subprocess.TimeoutExpired) as failure:
        monitor.reply(state, item.get("topic", ""), f"⛔ não apliquei o patch {item['patch_id']}: {failure}")
        events.record("patch", action="failed", id=item["patch_id"], reason=str(failure)[:300])
        return True
    for relative, content in files.items():
        with open(contained(AGENT_HOME, relative), "w") as handle:
            handle.write(content)
    paths = [os.path.join(AGENT_HOME, relative) for relative in files]
    run(["git", "-C", AGENT_HOME, "add", "--", *paths], AGENT_HOME, 60)
    message = f"fix(pepper): {item.get('summary', 'patch {{OWNER_FIRST_NAME}} approved')[:120]}"
    run(["git", "-C", AGENT_HOME, "-c", "user.name=Claude", "-c", "user.email=claude@localhost", "commit", "-q", "-m", message,
         "-m", f"Protected-file patch validated in an isolated copy and applied after {{OWNER_FIRST_NAME}}'s approval ({item['patch_id']}).",
         "--", *paths], AGENT_HOME, 60)
    sha = run(["git", "-C", AGENT_HOME, "rev-parse", "--short", "HEAD"], AGENT_HOME, 30).stdout.strip()
    monitor.reply(state, item.get("topic", ""), f"✅ patch aplicado em {sha}")
    events.record("patch", action="applied", id=item["patch_id"], commit=sha)
    log(f"protected patch {item['patch_id']} applied in {sha}")
    if item.get("threads") or item.get("rerequest") or item.get("reply"):
        state.setdefault("pending_thread_closes", []).append(
            {"ref": item["ref"], "sha": sha, "threads": item.get("threads", []), "rerequest": item.get("rerequest", []),
             "reply": item.get("reply", ""), "since": time.time()})
    return True


FIRST_COMMENT = "query($id:ID!){node(id:$id){... on PullRequestReviewThread{comments(first:1){nodes{databaseId}}}}}"


def close_threads(state, gh, log):
    waiting = []
    for item in state.get("pending_thread_closes", []):
        repo, number = item["ref"].split("#")
        try:
            full = json.loads(gh(["api", f"repos/{repo}/pulls/{number}"]) or "{}").get("head", {}).get("sha", "")
        except (RuntimeError, ValueError):
            full = ""
        head = full[:7] or item["sha"]
        for thread in item["threads"]:
            try:
                data = json.loads(gh(["api", "graphql", "-f", f"query={FIRST_COMMENT}", "-f", f"id={thread}"]) or "{}")
                comment = data["data"]["node"]["comments"]["nodes"][0]["databaseId"]
                gh(["api", "-X", "POST", f"repos/{repo}/pulls/{number}/comments/{comment}/replies", "-f",
                    f"body=Fixed in {head}: a patch validated in an isolated copy (every suite and the red team) and "
                    f"applied after the owner's approval."])
                gh(["api", "graphql", "-f", f"query=mutation{{resolveReviewThread(input:{{threadId:\"{thread}\"}}){{thread{{isResolved}}}}}}"])
            except (RuntimeError, ValueError, KeyError, IndexError, TypeError) as failure:
                log(f"could not close thread {thread} on {item['ref']}: {failure}")
        if item.get("reply"):
            try:
                gh(["api", "-X", "POST", f"repos/{repo}/issues/{number}/comments", "-f",
                    f"body={item['reply']}\n\nFixed in {head}."])
            except RuntimeError as failure:
                log(f"could not answer the review of {item['ref']}: {failure}")
        for login in item["rerequest"]:
            try:
                gh(["api", "-X", "POST", f"repos/{repo}/pulls/{number}/requested_reviewers", "-f", f"reviewers[]={login}"])
            except RuntimeError as failure:
                log(f"could not re-request {login} on {item['ref']}: {failure}")
        rule = CONFIG.get("ready_review", {}).get(repo, {})
        if item["rerequest"] and rule.get("slack_channel"):
            text = (f"{PREFIX} {rule.get('slack_names', '')}, corrigi os pontos de review em "
                    f"<https://github.com/{repo}/pull/{number}|{item['ref'].split('/', 1)[1]}> (commit {head}) e pedi "
                    f"review de vocês de novo.")
            claude.run_tool_calls([slack.send_call(rule["slack_channel"], "", text)], skill("slack-fetch"))
        pr = state.setdefault("prs", {}).setdefault(item["ref"], {})
        pr["review_rounds"] = pr.get("review_rounds", 0) + 1
        events.record("patch", action="threads_closed", ref=item["ref"], threads=item["threads"], sha=item["sha"])
    state["pending_thread_closes"] = waiting
