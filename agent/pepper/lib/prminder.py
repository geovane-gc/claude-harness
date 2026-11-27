import json
import re
import subprocess
import time

from . import claude, events, github, monitor, slack, workdays
from .settings import CONFIG, DRAFT_ONLY, GITHUB_ORGS, PREFIX, skill

BOTS = re.compile(r"(\[bot\]$|^claude$|^codecov|^github-actions|^dependabot|^sonarcloud|^renovate)", re.I)
# Repos where a merge applies or deploys on its own (infra, gitops): the minder never merges them (config: no_merge_repos).
NO_MERGE = set(CONFIG.get("no_merge_repos", []))
RELEASE_TYPES = ("feat", "fix", "perf", "refactor")
NO_RELEASE_TYPES = ("chore", "docs", "test", "ci", "build", "style")
CLAUDE_MARK = "Claude Code"
FAILED = {"FAILURE", "ERROR", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED", "STARTUP_FAILURE"}
PENDING = {"PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED", "WAITING", "REQUESTED"}


MAX_FIX_ATTEMPTS = 3
MAX_FIX_RUNS = 6
MAX_FLAKE_RERUNS = 3
FLAKY = re.compile(r"(runner has received a shutdown signal|lost communication with the server|exit code 130|The operation was canceled|ETIMEDOUT|ECONNRESET|503 Service "
                   r"Unavailable|502 Bad Gateway|Could not resolve host|rate limit exceeded|toomanyrequests|"
                   r"No space left on device)", re.I)
PLAIN_APPROVAL = re.compile(r"^(lgtm|looks good( to me)?|ship it|aprovado|aprovo|pode mergear|:shipit:|👍|✅|🚀)?[.!\s]*$", re.I)
KEEP_DRAFT = __import__("os").path.expanduser("~/{{HOME_DIR_NAME}}/pepper/keep_draft.json")


def keep_draft():
    try:
        with open(KEEP_DRAFT) as handle:
            return set(json.load(handle))
    except (OSError, ValueError):
        return set()


def failed_run_ids(repo, head, env):
    runs = json.loads(gh(["api", f"repos/{repo}/actions/runs?head_sha={head}&per_page=30"], env))
    return [r["id"] for r in runs.get("workflow_runs", [])
            if r.get("conclusion") in ("failure", "cancelled", "timed_out", "startup_failure")]


def within_budget(info, failed):
    if failed is not None:
        signature = "|".join(sorted(failed))
        if info.get("fix_signature") != signature:
            if info.get("fix_signature") is not None:
                info["fix_attempts"] = 0
            info["fix_signature"] = signature
        info.setdefault("fix_runs", info.get("fix_attempts", 0))
    return info.get("fix_attempts", 0) < MAX_FIX_ATTEMPTS and info.get("fix_runs", 0) < MAX_FIX_RUNS


def looks_flaky(repo, run_ids, env, attempt=None):
    for run_id in run_ids:
        path = f"repos/{repo}/actions/runs/{run_id}" + (f"/attempts/{attempt}" if attempt else "") + "/jobs?per_page=50"
        jobs = json.loads(gh(["api", path], env)).get("jobs", [])
        for job in jobs:
            if job.get("conclusion") not in ("failure", "cancelled", "timed_out"):
                continue
            done = subprocess.run([CONFIG["gh"], "api", f"repos/{repo}/actions/jobs/{job['id']}/logs"],
                                  capture_output=True, text=True, env=env, timeout=120)
            if FLAKY.search(done.stdout[-300000:]):
                return True
    return False


def gh(args, env, timeout=60):
    done = subprocess.run([CONFIG["gh"], *args], capture_output=True, text=True, env=env, timeout=timeout)
    if done.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {done.stderr.strip()[:300]}")
    return done.stdout


def open_prs(env):
    refs = []
    for org in GITHUB_ORGS:
        out = gh(["search", "prs", "--author", CONFIG["owner_github"], "--owner", org, "--state", "open",
                  "--limit", "50", "--json", "repository,number"], env)
        refs += [f"{org}/{p['repository']['name']}#{p['number']}" for p in json.loads(out)]
    return refs


def details(ref, env):
    repo, number = ref.split("#")
    view = json.loads(gh(["pr", "view", number, "-R", repo, "--json",
                          "isDraft,reviewDecision,mergeStateStatus,headRefOid,statusCheckRollup,reviews,comments,"
                          "body,title,url,commits,files"], env))
    owner, name = repo.split("/")
    query = ('query{repository(owner:"%s",name:"%s"){pullRequest(number:%s){reviewThreads(first:100){nodes{isResolved '
             'comments(last:1){nodes{author{login} createdAt}}}}}}}' % (owner, name, number))
    threads = json.loads(gh(["api", "graphql", "-f", f"query={query}"], env))
    view["threads"] = threads["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    return view


def checks_state(view):
    states = [(c.get("name") or c.get("context") or "?", (c.get("conclusion") or c.get("state") or "").upper())
              for c in view.get("statusCheckRollup") or []]
    failed = sorted({n for n, s in states if s in FAILED})
    pending = sorted({n for n, s in states if s in PENDING or s == ""})
    return ("red" if failed else "pending" if pending else "green"), failed


def human(login):
    return login and login != CONFIG["owner_github"] and not BOTS.search(login)


def last_activity(view):
    stamps = {"others": "", "owner": ""}
    for c in view.get("comments", []):
        key = "owner" if c["author"]["login"] == CONFIG["owner_github"] else ("others" if human(c["author"]["login"]) else None)
        if key:
            stamps[key] = max(stamps[key], c.get("createdAt", ""))
    for r in view.get("reviews", []):
        login = r["author"]["login"]
        plain_approval = r["state"] == "APPROVED" and PLAIN_APPROVAL.match((r.get("body") or "").strip())
        if human(login) and not plain_approval and (r.get("body") or r["state"] == "CHANGES_REQUESTED"):
            stamps["others"] = max(stamps["others"], r.get("submittedAt", ""))
        elif login == CONFIG["owner_github"]:
            stamps["owner"] = max(stamps["owner"], r.get("submittedAt", ""))
    for t in view.get("threads", []):
        node = (t.get("comments", {}).get("nodes") or [{}])[0]
        login = (node.get("author") or {}).get("login", "")
        if not t["isResolved"] and human(login):
            stamps["others"] = max(stamps["others"], node.get("createdAt", ""))
    return stamps


def unanswered(view):
    stamps = last_activity(view)
    open_threads = [t for t in view.get("threads", []) if not t["isResolved"]
                    and human(((t.get("comments", {}).get("nodes") or [{}])[0].get("author") or {}).get("login", ""))]
    return bool(stamps["others"] and stamps["others"] > stamps["owner"]) or bool(open_threads)


def type_of(text):
    match = re.match(r"^(\w+)(\(|:)", text or "")
    return match.group(1) if match else ""


def merge_blocker(ref, view, check):
    repo = ref.split("/")[1].split("#")[0]
    if repo in NO_MERGE:
        return f"merge em {repo} aplica/deploya na hora: decisão do {{OWNER_FIRST_NAME}}"
    if view["isDraft"]:
        return "draft"
    if view.get("reviewDecision") != "APPROVED":
        return "sem aprovação"
    if check != "green":
        return "CI não está verde"
    if view.get("mergeStateStatus") != "CLEAN":
        return f"mergeStateStatus {view.get('mergeStateStatus')}"
    if unanswered(view):
        return "comentários sem resposta"
    title_type = type_of(view["title"])
    commits = view.get("commits") or []
    if len(commits) == 1 and type_of(commits[0].get("messageHeadline", "")) != title_type:
        return "tipo do commit único difere do título (squash usa o commit)"
    code = [f["path"] for f in view.get("files") or []
            if not re.search(r"(\.md$|^docs/|(^|/)tests?/|(^|/)__tests__/|[._]test\.|Test\.|^\.github/)", f["path"])]
    if title_type in NO_RELEASE_TYPES and code:
        return f"tipo '{title_type}' não gera release, mas muda código de produção"
    return ""


def tick(state, env, log, start_threads_run, start_fix_run):
    prs = state.setdefault("prs", {})
    try:
        refs = open_prs(env)
    except RuntimeError as failure:
        monitor.error(state, "pr_minder", str(failure))
        return
    for ref in refs:
        if ref in prs:
            prs[ref].pop("closed_seen", None)
        try:
            mind(state, prs, ref, env, log, start_threads_run, start_fix_run)
        except Exception as failure:
            log(f"pr-minder {ref}: {failure!r}")
            events.record("pr_minder", ref=ref, action="error", error=repr(failure)[:300])
    for ref in list(prs):
        if ref not in refs and time.time() - prs[ref].get("closed_seen", time.time()) > 14 * 86400:
            del prs[ref]
        elif ref not in refs:
            prs[ref].setdefault("closed_seen", time.time())


def announce_ready(rule, ref, view):
    text = (f"{PREFIX} {rule.get('slack_names', '')}, pedi review de vocês em <{view['url']}|{ref.split('/', 1)[1]}>: "
            f"{view.get('title', '')[:120]} (CI verde; esse repo não avisa no Slack sozinho)")
    claude.run_tool_calls([slack.send_call(rule["slack_channel"], "", text)], skill("slack-fetch"))


def mind(state, prs, ref, env, log, start_threads_run, start_fix_run):
    try:
        view = details(ref, env)
    except (RuntimeError, TypeError, KeyError) as failure:
        log(f"pr-minder {ref}: {failure}")
        return
    info = prs.setdefault(ref, {})
    check, failed = checks_state(view)
    header = f"🔀 Seu PR {ref.split('/', 1)[1]}: {view.get('title', '')[:120]} — {view['url']}"
    info["view"] = {"title": view.get("title", "")[:100], "url": view["url"], "draft": view["isDraft"],
                    "check": check, "decision": view.get("reviewDecision") or "", "at": time.time()}
    head = view["headRefOid"]
    if check == "red" and info.get("red_notified") != head:
        repo_name = ref.split("#")[0]
        failed_runs = failed_run_ids(repo_name, head, env)
        first = info.get("rerun") != head
        flaky = not first and info.get("flake_reruns", {}).get(head, 0) < MAX_FLAKE_RERUNS and \
            looks_flaky(repo_name, failed_runs, env)
        if failed_runs and (first or flaky):
            info["rerun"] = head
            if flaky:
                info.setdefault("flake_reruns", {})[head] = info.get("flake_reruns", {}).get(head, 0) + 1
            for run_id in failed_runs:
                gh(["run", "rerun", str(run_id), "--failed", "-R", repo_name], env)
            why = "falha de infraestrutura (runner/timeout)" if flaky else "caso tenha sido o runner"
            monitor.open_topic(state, ref, header)
            monitor.reply(state, ref, f"🔁 CI falhou em {head[:7]} ({', '.join(failed)[:200]}); rodei os jobs "
                                      f"falhos de novo: {why}")
            events.record("pr_minder", ref=ref, action="ci_rerun", checks=failed, flaky=flaky)
            monitor.phase(state, ref, "ci_rerun")
            return
    fixable = (not DRAFT_ONLY and CLAUDE_MARK in (view.get("body") or "") and within_budget(info, failed if check == "red" else None)
               and ref.split("/")[1].split("#")[0] not in CONFIG.get("no_fix_repos", []))
    if check == "red" and info.get("fix_head") != head and fixable and ref not in state.get("prfix_running", []):
        info["fix_head"] = head
        info["fix_attempts"] = info.get("fix_attempts", 0) + 1
        info["fix_runs"] = info.get("fix_runs", 0) + 1
        monitor.open_topic(state, ref, header)
        monitor.reply(state, ref, f"🔧 CI ainda vermelho em {head[:7]} ({', '.join(failed)[:200]}): tentando corrigir "
                                  f"(tentativa {info['fix_attempts']}/{MAX_FIX_ATTEMPTS})")
        events.record("pr_minder", ref=ref, action="fix_started", checks=failed, attempt=info["fix_attempts"])
        monitor.phase(state, ref, "ci_red")
        reason = f"CI red on {head[:7]}: {', '.join(failed)}"
        start_fix_run(state, ref, view["url"], reason, [])
        return
    if check == "red" and info.get("fix_head") == head:
        return
    if check == "green":
        info.pop("needs_you", None)
    if check == "red" and info.get("red_notified") != head:
        info["red_notified"] = head
        info["needs_you"] = (f"CI vermelho ({', '.join(failed)[:120]}) depois de {info.get('fix_attempts', 0)} "
                             f"tentativa(s) neste erro ({info.get('fix_runs', 0)} no PR)" if info.get("fix_attempts") else
                             f"CI vermelho ({', '.join(failed)[:120]}) num PR sem a marca do Claude")
        monitor.open_topic(state, ref, header)
        monitor.root(state, f"pr:{ref}:red:{head[:7]}", f"🔴 CI falhou em {ref.split('/', 1)[1]} ({head[:7]}): "
                                                        f"{', '.join(failed)[:300]} — {view['url']}")
        events.record("pr_minder", ref=ref, action="ci_red", checks=failed)
        monitor.phase(state, ref, "ci_red")
    if (DRAFT_ONLY and check == "green" and view["isDraft"] and CLAUDE_MARK in (view.get("body") or "")
            and ref not in keep_draft() and info.get("ready_told") != head):
        info["ready_told"] = head
        monitor.open_topic(state, ref, header)
        monitor.root(state, f"pr:{ref}:green:{head[:7]}", f"🟢 {ref.split('/', 1)[1]}: CI verde e ainda em draft. "
                                                          f"Modo só rascunhos: não tirei do draft nem pedi review — {view['url']}")
    if (not DRAFT_ONLY and check == "green" and view["isDraft"] and CLAUDE_MARK in (view.get("body") or "")
            and ref not in keep_draft() and info.get("readied") != head and workdays.is_workday()):
        repo, number = ref.split("#")
        gh(["pr", "ready", number, "-R", repo], env)
        info["readied"] = head
        rule = CONFIG.get("ready_review", {}).get(repo, {})
        reviewers = list(dict.fromkeys(state.get("review_on_ready", {}).pop(ref, []) + rule.get("reviewers", [])))
        for login in reviewers:
            gh(["api", "-X", "POST", f"repos/{repo}/pulls/{number}/requested_reviewers", "-f", f"reviewers[]={login}"], env)
        if rule.get("slack_channel"):
            announce_ready(rule, ref, view)
        monitor.open_topic(state, ref, header)
        told = (f"pedi review a {', '.join(reviewers)}" + (" e avisei no grupo" if rule.get("slack_channel") else "")
                if reviewers else "o repo avisa o time no Slack")
        monitor.root(state, f"pr:{ref}:ready:{head[:7]}", f"🟢 {ref.split('/', 1)[1]}: CI verde, tirei do draft; "
                                                          f"{told} — {view['url']}")
        events.record("pr_minder", ref=ref, action="ready")
        monitor.phase(state, ref, "ready")
    stamps = last_activity(view)
    if stamps["others"] and stamps["others"] > info.get("handled_others", "") and unanswered(view) and DRAFT_ONLY:
        info["handled_others"] = stamps["others"]
        monitor.open_topic(state, ref, header)
        monitor.root(state, f"pr:{ref}:comments:{stamps['others']}", f"💬 {ref.split('/', 1)[1]}: comentário novo de "
                                                                      f"revisor sem resposta. Modo só rascunhos: não "
                                                                      f"respondi — {view['url']}")
    elif stamps["others"] and stamps["others"] > info.get("handled_others", "") and unanswered(view):
        if ref not in state.get("pr_threads_running", []):
            info["handled_others"] = stamps["others"]
            start_threads_run(state, ref, view["url"])
    blocker = merge_blocker(ref, view, check)
    if not blocker and info.get("merged") != head and CONFIG.get("pr_minder_merge", False) and workdays.is_workday():
        repo, number = ref.split("#")
        gh(["pr", "merge", number, "-R", repo, "--squash"], env, timeout=120)
        info["merged"] = head
        monitor.open_topic(state, ref, header)
        monitor.root(state, f"pr:{ref}:merged", f"🟣 {ref.split('/', 1)[1]} mergeado (aprovado, comentários "
                                                f"respondidos, CI verde) — {view['url']}")
        events.record("pr_minder", ref=ref, action="merged")
        monitor.phase(state, ref, "merged")
    elif blocker and view.get("reviewDecision") == "APPROVED" and info.get("blocked_note") != f"{head}:{blocker}":
        info["blocked_note"] = f"{head}:{blocker}"
        monitor.open_topic(state, ref, header)
        monitor.root(state, f"pr:{ref}:blocked:{head[:7]}", f"⏸️ {ref.split('/', 1)[1]} aprovado, mas não mergeei: "
                                                            f"{blocker} — {view['url']}")
        events.record("pr_minder", ref=ref, action="merge_blocked", reason=blocker)
        monitor.phase(state, ref, "blocked")
