import json
import os
import re
import subprocess

from .settings import CONFIG, DEFAULT_ORG, clean_env

PR_LINK = re.compile(r"github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)")


REPO_SHORT = re.compile(r"(?<![\w/.-])([a-z][\w.-]*[\w])#(\d+)\b")
BARE_NUMBER = re.compile(r"(?<![\w/])#(\d+)\b")
CLONES = os.path.expanduser("~/{{HOME_DIR_NAME}}/repos")


def known_repos():
    try:
        return {name for name in os.listdir(CLONES) if not name.startswith(".")}
    except OSError:
        return set()


def pr_refs(text):
    text = text.replace("\\/", "/")
    refs = {f"{org}/{repo}#{number}" for org, repo, number in PR_LINK.findall(text)}
    repos = known_repos()
    refs |= {f"{DEFAULT_ORG}/{repo}#{number}" for repo, number in REPO_SHORT.findall(text) if repo in repos and DEFAULT_ORG}
    named = {repo for repo in repos if re.search(r"(?<![\w/.-])" + re.escape(repo) + r"(?![\w-])", text)}
    if len(named) == 1 and DEFAULT_ORG:
        repo = named.pop()
        refs |= {f"{DEFAULT_ORG}/{repo}#{number}" for number in BARE_NUMBER.findall(REPO_SHORT.sub("", text))}
    return sorted(refs)


def token():
    done = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                          capture_output=True, text=True, env=dict(clean_env(), GIT_TERMINAL_PROMPT="0"), timeout=30)
    match = re.search(r"^password=(.+)$", done.stdout, re.M)
    if not match:
        raise RuntimeError("no GitHub credential in git's credential helper")
    return match.group(1)


TOKEN_CACHE = {"value": "", "at": 0.0}
TOKEN_SECONDS = 600


def gh_env():
    import time
    if not TOKEN_CACHE["value"] or time.time() - TOKEN_CACHE["at"] > TOKEN_SECONDS:
        TOKEN_CACHE.update(value=token(), at=time.time())
    return clean_env({"GH_TOKEN": TOKEN_CACHE["value"]})


NOT_FOUND = re.compile(r"Could not resolve to a (PullRequest|Repository)|HTTP 404|not found", re.I)


class TransientError(RuntimeError):
    pass


def pr_status(ref, env):
    repo, number = ref.split("#")
    done = subprocess.run([CONFIG["gh"], "pr", "view", number, "-R", repo, "--json",
                           "state,isDraft,mergeable,author,headRefOid,reviews,comments,url,title"],
                          capture_output=True, text=True, env=env, timeout=60)
    if done.returncode != 0:
        error = (done.stderr or done.stdout).strip()[:300]
        if NOT_FOUND.search(error):
            return {"error": error}
        raise TransientError(f"{ref}: {error}")
    return json.loads(done.stdout)


def decide(ref, status, owner_login, asked_directly=False):
    if "error" in status:
        return "skip", "not found: " + status["error"]
    if status["author"]["login"] == owner_login:
        return "skip", "own PR"
    if status["state"] != "OPEN":
        return "skip", status["state"].lower()
    if status["isDraft"]:
        return "skip", "draft"
    if status["mergeable"] == "CONFLICTING":
        return "skip", "conflict"
    mine = [r for r in status["reviews"] if r["author"]["login"] == owner_login]
    commented = any(c["author"]["login"] == owner_login for c in status["comments"])
    if not mine and not commented:
        return "review", ""
    last = mine[-1] if mine else None
    moved = bool(last) and last.get("commit", {}).get("oid") != status["headRefOid"]
    if last and last["state"] == "CHANGES_REQUESTED":
        return ("re-review", "") if moved else ("skip", "changes requested, no new commit")
    if last and last["state"] == "DISMISSED" and moved:
        return "re-review", ""
    if asked_directly and moved and last["state"] in ("COMMENTED", "DISMISSED"):
        return "re-review", ""
    return "skip", "already reviewed" + (f" ({last['state'].lower()})" if last else "")


WRITE_PERMISSIONS = {"admin", "maintain", "write"}
THREAD_QUERY = ("query($id:ID!){node(id:$id){... on PullRequestReviewThread{comments(first:1){nodes{body author{login}}}}}}")


def run_gh(args, env, timeout=60):
    done = subprocess.run([CONFIG["gh"], *args], capture_output=True, text=True, env=env, timeout=timeout)
    if done.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args[:3])}: {(done.stderr or done.stdout).strip()[:300]}")
    return done.stdout


def can_write(repo, login, env):
    try:
        data = json.loads(run_gh(["api", f"repos/{repo}/collaborators/{login}/permission"], env))
    except (RuntimeError, ValueError, subprocess.TimeoutExpired):
        return False
    return data.get("permission") in WRITE_PERMISSIONS or data.get("role_name") in WRITE_PERMISSIONS


def trusted_points(ref, points, env):
    repo = ref.split("#")[0]
    kept, dropped = [], []
    number = ref.split("#")[1]
    for point in points or []:
        if point.get("review_id"):
            try:
                review = json.loads(run_gh(["api", f"repos/{repo}/pulls/{number}/reviews/{int(point['review_id'])}"], env))
                login, body = review["user"]["login"], review.get("body") or ""
            except (RuntimeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired):
                dropped.append(f"review {point.get('review_id')}")
                continue
            if body.strip() and can_write(repo, login, env):
                kept.append({"review_id": str(point["review_id"]), "author": login, "text": body[:4000]})
            else:
                dropped.append(f"review {point.get('review_id')}")
            continue
        try:
            data = json.loads(run_gh(["api", "graphql", "-f", f"query={THREAD_QUERY}", "-f", f"id={point.get('thread_id', '')}"], env))
            comment = data["data"]["node"]["comments"]["nodes"][0]
            login, body = comment["author"]["login"], comment["body"]
        except (RuntimeError, ValueError, KeyError, IndexError, TypeError, subprocess.TimeoutExpired):
            dropped.append(point.get("thread_id", "?"))
            continue
        if can_write(repo, login, env):
            kept.append({"thread_id": point["thread_id"], "author": login, "text": body[:2000]})
        else:
            dropped.append(point.get("thread_id", "?"))
    return kept, dropped
