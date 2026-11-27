import json
import os
import re
import subprocess

from .settings import CONFIG

CONTRACT = re.compile(r"(/gateways?/|/producers?/|/consumers?/|/mappers?/|/routes?/|/requests?/|/responses?/|/migrations?/|"
                      r"openapi|\.proto$|schema|libs\.versions\.toml$|build\.gradle|package\.json$|go\.mod$|"
                      r"pyproject\.toml$|Cargo\.toml$)")
# Infra and docs repos a smaller model reviews well enough (config: light_review_repos).
LIGHT_REPOS = set(CONFIG.get("light_review_repos", []))
DOCS = re.compile(r"(\.md$|^docs/|\.lock$|gradle\.lockfile$|/snapshots?/)")


def choose(ref, mode, env):
    if mode == "re-review":
        return {"model": "sonnet", "effort": "high", "why": "re-review checks only the blocking points"}
    repo, number = ref.split("#")
    try:
        done = subprocess.run([CONFIG["gh"], "pr", "view", number, "-R", repo, "--json", "additions,deletions,files"],
                              capture_output=True, text=True, env=env, timeout=60)
        view = json.loads(done.stdout)
    except (ValueError, subprocess.TimeoutExpired):
        return {"model": "opus", "effort": "high", "why": "could not size the PR"}
    paths = [f["path"] for f in view.get("files") or []]
    lines = (view.get("additions") or 0) + (view.get("deletions") or 0)
    code = [p for p in paths if not DOCS.search(p)]
    name = repo.split("/")[1]
    if not code:
        return {"model": "sonnet", "effort": "medium", "why": f"docs/lockfiles only ({lines} lines)"}
    if any(CONTRACT.search(p) for p in code) or lines > 400:
        return {"model": "opus", "effort": "high", "why": f"contract/config/migration paths or large diff ({lines} lines)"}
    if name in LIGHT_REPOS or lines < 80:
        return {"model": "sonnet", "effort": "high", "why": f"{'infra/docs repo' if name in LIGHT_REPOS else 'small diff'} ({lines} lines)"}
    return {"model": "sonnet", "effort": "high", "why": f"internal change without contract paths ({lines} lines)"}


REPOS = os.path.expanduser("~/{{HOME_DIR_NAME}}/repos")
BUILD_RISK = re.compile(r"(migra|contrat|contract|consumer|producer|gateway|extension|\blib\b|starter|\bbump|"
                        r"seguran|security|\bguard|\bprod\b|payment|\blimit|dinheiro|money|índice|\bindex|schema|"
                        r"\bevento|\bevents?\b|mapper|\bresponse|\brequest|\broute|endpoint|\bapi\b|payload)", re.I)
PEPPER_LIGHT_KINDS = ("improve", "routine", "tracking", "other")


def known_repos(text):
    known = set(os.listdir(REPOS)) if os.path.isdir(REPOS) else set()
    named = {name for name in known if re.search(r"\b" + re.escape(name) + r"\b", text)}
    return sorted(named - {CONFIG.get("harness_repo", "").split("/")[-1]})


def choose_build(line):
    kind = (re.search(r"\((\w+)\)", line) or [None, "other"])[1]
    repos = known_repos(line)
    retried = re.search(r"reopened \S+: build (blocked|failed)", line)
    if retried:
        return {"model": "opus", "effort": "high", "why": "a previous build of this item was blocked or failed"}
    if kind == "debug":
        return {"model": "opus", "effort": "high", "why": "debugging needs the strongest model"}
    if repos:
        if len(repos) > 1 or BUILD_RISK.search(line):
            return {"model": "opus", "effort": "high",
                    "why": f"product code with risk (repos: {', '.join(repos[:4])}{'…' if len(repos) > 4 else ''})"}
        return {"model": "sonnet", "effort": "high", "why": f"one product repo, no contract or risk words ({repos[0]})"}
    if BUILD_RISK.search(line) and kind == "develop":
        return {"model": "opus", "effort": "high", "why": "agent change touching security, prod or contracts"}
    if kind in PEPPER_LIGHT_KINDS:
        return {"model": "sonnet", "effort": "medium", "why": f"agent {kind}: skill, prompt or knowledge change"}
    return {"model": "sonnet", "effort": "high", "why": "agent code change without risk words"}


LIGHT_FIX = re.compile(r"(codecov|coverage|lint|format|scan|security|cve|title)", re.I)


def choose_fix(reason, points):
    if points:
        risky = any(BUILD_RISK.search(p.get("text", "")) for p in points)
        return {"model": "opus" if risky else "sonnet", "effort": "high",
                "why": "reviewer points touching contracts or risk" if risky else "reviewer points, plain code changes"}
    checks = reason.split(":", 1)[-1]
    if LIGHT_FIX.search(checks) and not re.search(r"\b(unit|integration|test)s?\b", checks.replace("Lint and Test", ""), re.I):
        return {"model": "sonnet", "effort": "high", "why": "coverage, lint or a scanner"}
    return {"model": "opus", "effort": "high", "why": "failing tests or build: needs the strongest model"}
