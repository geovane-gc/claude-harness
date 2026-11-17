#!/usr/bin/env python3
"""Posts one review on a pull request: the general message and each comment on its line of the diff.

Usage: post-review.py <pr url> <review file>

The review file is JSON:
  {"commit": "<the commit that was reviewed>",
   "event": "COMMENT" | "REQUEST_CHANGES" | "APPROVE",
   "body": "<the general message>",
   "comments": [{"path": "<file>", "line": <line of the new file>, "body": "<text>"}]}

Everything goes to GitHub in one call, so the review is posted whole or not at all. Nothing is posted
(exit 1) when the pull request's head is no longer the commit reviewed, when a comment is not on a line
of the diff (it prints the lines that are), or when the event is one GitHub refuses on your own pull
request. Prints the review's URL.
"""
import json
import re
import subprocess
import sys

USAGE = "usage: post-review.py <pr url> <review file>"
EVENTS = ("COMMENT", "REQUEST_CHANGES", "APPROVE")


def stop(message: str) -> None:
    print(f"STOP: nothing posted. {message}", file=sys.stderr)
    sys.exit(1)


def gh(*args: str, data: str | None = None) -> str:
    done = subprocess.run(["gh", "api", *args], input=data, capture_output=True, text=True)
    if done.returncode != 0:
        stop(f"gh api {' '.join(args)} failed: {done.stderr.strip()[:300]}")
    return done.stdout


def pages(text: str) -> list:
    """The items of a paginated answer: gh prints one JSON array per page, one after the other."""
    items, decoder, at = [], json.JSONDecoder(), 0
    while at < len(text):
        if text[at].isspace():
            at += 1
            continue
        page, at = decoder.raw_decode(text, at)
        items.extend(page)
    return items


def new_lines(patch: str) -> set:
    """The line numbers of the new file that a patch shows: the lines GitHub accepts a comment on."""
    lines, number = set(), 0
    rows = patch.split("\n")
    for index, row in enumerate(rows):
        hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", row)
        if hunk:
            number = int(hunk.group(1))
        elif row.startswith("+") or row.startswith(" ") or (row == "" and index < len(rows) - 1):
            lines.add(number)
            number += 1
    return lines


def ranges(lines: set) -> str:
    out, run = [], []
    for n in sorted(lines):
        if run and n == run[-1] + 1:
            run.append(n)
            continue
        if run:
            out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
        run = [n]
    if run:
        out.append(f"{run[0]}-{run[-1]}" if len(run) > 1 else str(run[0]))
    return ", ".join(out) or "none"


def main() -> None:
    if len(sys.argv) != 3:
        stop(USAGE)
    url, path = sys.argv[1], sys.argv[2]
    where = re.match(r"https://github\.com/([^/]+/[^/]+)/pull/(\d+)", url)
    if not where:
        stop(f'Give the pull request\'s URL, not "{url}".')
    repo, number = where.group(1), where.group(2)
    try:
        review = json.load(open(path))
    except (OSError, ValueError) as error:
        stop(f"The review file {path} cannot be read as JSON: {error}")
    comments = review.get("comments")
    well_formed = (
        isinstance(review.get("commit"), str) and review.get("event") in EVENTS
        and isinstance(review.get("body"), str) and review["body"].strip()
        and isinstance(comments, list)
        and all(isinstance(c.get("path"), str) and isinstance(c.get("line"), int)
                and isinstance(c.get("body"), str) and c["body"].strip() for c in comments)
    )
    if not well_formed:
        stop("The review file needs commit, event (COMMENT, REQUEST_CHANGES or APPROVE), a body, "
             "and comments that each have path, line and body.")

    pull = json.loads(gh(f"repos/{repo}/pulls/{number}"))
    head = pull["head"]["sha"]
    if not review["commit"] or not head.startswith(review["commit"]):
        stop(f"The pull request is now at {head[:7]}, and the review was written on {review['commit'][:7]}: "
             "review the new commit first.")
    if review["event"] != "COMMENT" and pull["user"]["login"] == json.loads(gh("user"))["login"]:
        stop(f"GitHub refuses {review['event']} on your own pull request: use COMMENT.")

    shown = {f["filename"]: new_lines(f.get("patch") or "")
             for f in pages(gh(f"repos/{repo}/pulls/{number}/files", "--paginate"))}
    wrong = []
    for c in comments:
        if c["path"] not in shown:
            wrong.append(f"  {c['path']}:{c['line']}: the pull request does not change this file")
        elif c["line"] not in shown[c["path"]]:
            wrong.append(f"  {c['path']}:{c['line']}: not a line of the diff; its lines there are {ranges(shown[c['path']])}")
    if wrong:
        stop("These comments are not on a line of the diff:\n" + "\n".join(wrong))

    payload = {"commit_id": head, "event": review["event"], "body": review["body"],
               "comments": [{"path": c["path"], "line": c["line"], "side": "RIGHT", "body": c["body"]} for c in comments]}
    posted = json.loads(gh("--method", "POST", f"repos/{repo}/pulls/{number}/reviews", "--input", "-", data=json.dumps(payload)))
    print(f"POSTED: {posted.get('html_url')} ({review['event']}, {len(comments)} comments on the diff)")


if __name__ == "__main__":
    main()
