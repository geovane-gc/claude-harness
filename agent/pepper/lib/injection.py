import json
import re
import subprocess

from .settings import CONFIG

INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤⁦-⁩﻿\U000e0000-\U000e007f]")
AIMED_AT_REVIEWERS = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier|your)\s+(instructions|rules|prompt)"
    r"|ignor(e|a|ar)\s+(as\s+|todas\s+as\s+)?instru[cç](ões|oes)"
    r"|\b(you are|you're|acting as) (an? )?(ai|llm|language model|assistant|claude|automated reviewer)\b"
    r"|\b(ai|automated|llm|bot)[ -]?reviewers?\b"
    r"|\b(please\s+)?(auto[- ]?)?approve (this|the) (pr|pull request|change)"
    r"|\baprov(e|a|ar) (este|esse|o) (pr|pull request)"
    r"|\blgtm (is )?required\b|\bmust (be )?approve"
    r"|system prompt|<\s*/?\s*(system|instructions?)\s*>|\[\s*(system|inst)\s*\]", re.I)


def added_lines(diff):
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            yield line[1:]


def findings(texts):
    found = []
    for where, text in texts:
        for number, line in enumerate(text.splitlines(), 1):
            if INVISIBLE.search(line):
                found.append(f"{where}:{number} invisible or bidirectional character")
            match = AIMED_AT_REVIEWERS.search(line)
            if match:
                found.append(f"{where}:{number} \"{match.group(0)[:60]}\"")
    return found


UNREADABLE = "the PR could not be read completely, so it was not scanned"


def gh_output(args, env, timeout):
    done = subprocess.run([CONFIG["gh"], *args], capture_output=True, text=True, env=env, timeout=timeout)
    if done.returncode != 0:
        raise ValueError(done.stderr[:100])
    return done.stdout


def scan(ref, env):
    repo, number = ref.split("#")
    try:
        view = json.loads(gh_output(["pr", "view", number, "-R", repo, "--json", "title,body"], env, 60))
        diff = gh_output(["pr", "diff", number, "-R", repo], env, 120)
        talk = json.loads(gh_output(["pr", "view", number, "-R", repo, "--json", "comments,reviews"], env, 60))
        pages = json.loads(gh_output(["api", f"repos/{repo}/pulls/{number}/comments", "--paginate", "--slurp"], env, 60))
        inline = [c for page in pages for c in (page if isinstance(page, list) else [page])]
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return [UNREADABLE]
    texts = [("title", view.get("title") or ""), ("body", view.get("body") or ""),
             ("diff", "\n".join(added_lines(diff)))]
    texts +=[(f"comment by {c.get('author', {}).get('login', '?')}", c.get("body") or "") for c in talk.get("comments") or []]
    texts += [(f"review by {r.get('author', {}).get('login', '?')}", r.get("body") or "") for r in talk.get("reviews") or []]
    texts += [(f"inline comment by {(c.get('user') or {}).get('login', '?')}", c.get("body") or "")
              for c in inline if isinstance(c, dict)]
    return findings(texts)[:10]
