import json
import os
import re

PEPPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(PEPPER, "state")
LOG_DIR = os.path.join(PEPPER, "logs")
SKILLS = os.path.join(PEPPER, "skills")

with open(os.path.join(PEPPER, "config.json")) as handle:
    CONFIG = json.load(handle)

OWNER = CONFIG["owner_slack_id"]
PREFIX = CONFIG["prefix"]
AGENT_NAME = CONFIG.get("agent_name") or "agent"
# While on, nothing goes out on the agent's own: replies, reviews and PR answers become questions and drafts in the
# control channel. Only a draft the owner approved with ✅ and the owner's own orders reach anyone else.
DRAFT_ONLY = CONFIG.get("draft_only", True)
# How the owner is named in a message (first name, surname, nickname), lowercase, for the injection screen.
OWNER_NAMES = [name.lower() for name in CONFIG.get("owner_names", []) if name.strip()]
WORKSPACE = os.path.expanduser(CONFIG["workspace"])
# The Slack workspace host (yourteam.slack.com): permalinks are built and checked against it.
SLACK_HOST = CONFIG["slack_workspace_host"].strip().lower().rstrip("/")
SLACK_URL = f"https://{SLACK_HOST}/"
# The GitHub organizations whose repos the agent works on; the first one names a bare `repo#123`.
GITHUB_ORGS = [org for org in CONFIG.get("github_orgs", []) if org]
DEFAULT_ORG = GITHUB_ORGS[0] if GITHUB_ORGS else ""


def slack_link(channel, ts):
    return f"{SLACK_URL}archives/{channel}/p{ts.replace('.', '')}"


def inside(directory, path):
    base, real = os.path.realpath(directory), os.path.realpath(path)
    if os.path.commonpath([base, real]) != base:
        raise ValueError(f"refusing a path outside {directory}: {path}")
    return real


def inside_logs(path):
    return inside(LOG_DIR, path)


def log_file(path, mode="r"):
    name = os.path.basename(inside_logs(path))
    os.makedirs(LOG_DIR, exist_ok=True)
    directory = os.open(LOG_DIR, os.O_RDONLY)
    try:
        flags = os.O_RDONLY if mode == "r" else os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        descriptor = os.open(name, flags, 0o600, dir_fd=directory)
    finally:
        os.close(directory)
    return os.fdopen(descriptor, mode)


INCLUDE = re.compile(r"^@include (\S+)$", re.M)


def skill(name):
    path = inside(SKILLS, os.path.join(SKILLS, name, "SKILL.md"))
    with open(path) as handle:
        text = handle.read()
    if not INCLUDE.search(text):
        return path

    def included(match):
        with open(inside(SKILLS, os.path.join(SKILLS, match.group(1)))) as part:
            return part.read().rstrip("\n")

    expanded = INCLUDE.sub(included, text)
    built_dir = os.path.join(STATE_DIR, "skills")
    built = inside(built_dir, os.path.join(built_dir, f"{name}.md"))
    os.makedirs(built_dir, exist_ok=True)
    temporary = inside(built_dir, built + ".tmp")
    with open(temporary, "w") as handle:
        handle.write(expanded)
    os.replace(temporary, built)
    return built


def clean_env(extra=None):
    env = {"HOME": os.environ["HOME"], "USER": os.environ.get("USER", ""),
           "LANG": "en_US.UTF-8", "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"}
    env.update(extra or {})
    return env
