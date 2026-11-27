import hashlib
import os
import shutil
import subprocess
import time

AGENT_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WATCHED = ["pepper/guard", "pepper/config.json", "pepper/keep_draft.json", "plugin/hooks", "bin/secret",
           "knowledge/security-policy.md", "pepper/launchd", "bin/backlog"]
UNWATCHED = {".git", "worktrees", "repos", "research", "pepper/logs", "pepper/state"}
RUNNING_CODE = ["pepper/watch.py", "pepper/lib", "pepper/skills", "pepper/guard", "bin", "plugin", "claude", "hooks",
                "git-hooks"]
ASIDE = os.path.join(AGENT_HOME, "pepper", "state", "integrity")


def tracked_files():
    done = subprocess.run(["git", "-C", AGENT_HOME, "ls-files", "-z"], capture_output=True, text=True, timeout=60)
    return sorted(os.path.join(AGENT_HOME, p) for p in done.stdout.split("\0")
                  if p and not p.startswith(("worktrees/", "repos/")) and os.path.isfile(os.path.join(AGENT_HOME, p)))


def present_files():
    found = []
    for folder, subfolders, names in os.walk(AGENT_HOME):
        relative = os.path.relpath(folder, AGENT_HOME)
        subfolders[:] = [s for s in subfolders if os.path.normpath(os.path.join(relative, s)) not in UNWATCHED]
        found += [os.path.join(folder, name) for name in names]
    return found


def running_code(path):
    relative = os.path.relpath(path, AGENT_HOME)
    in_scope = any(relative == part or relative.startswith(part + "/") for part in RUNNING_CODE + WATCHED)
    loose_python = os.path.dirname(relative) == "pepper" and relative.endswith(".py")
    return (in_scope or loose_python) and not relative.endswith((".pyc", ".tmp")) and "__pycache__" not in relative


def files(whole=False):
    if whole:
        return sorted(path for path in set(tracked_files()) | set(present_files()) if running_code(path))
    found = []
    for part in WATCHED:
        path = os.path.join(AGENT_HOME, part)
        if os.path.isdir(path):
            for folder, _, names in os.walk(path):
                found += [os.path.join(folder, n) for n in names if not n.endswith((".pyc", ".tmp")) and "__pycache__" not in folder]
        elif os.path.exists(path):
            found.append(path)
    return sorted(found)


def digest(path):
    if os.path.islink(path):
        return "link:" + os.readlink(path)
    if not os.path.isfile(path):
        return "special"
    base_real = os.path.realpath(AGENT_HOME)
    target_real = os.path.realpath(path)
    if os.path.commonpath([base_real, target_real]) != base_real:
        return "outside"
    try:
        with open(target_real, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return "unreadable"


def snapshot(whole=False):
    return {os.path.relpath(path, AGENT_HOME): digest(path) for path in files(whole)}


def committed(path):
    done = subprocess.run(["git", "-C", AGENT_HOME, "diff", "--quiet", "HEAD", "--", path], capture_output=True, timeout=30)
    tracked = subprocess.run(["git", "-C", AGENT_HOME, "ls-files", "--error-unmatch", path], capture_output=True, timeout=30)
    return done.returncode == 0 and tracked.returncode == 0


def changed(before, whole=False):
    after = snapshot(whole)
    moved = [path for path in set(before) | set(after) if before.get(path) != after.get(path)]
    return sorted(path for path in moved if not committed(path))


def set_aside(paths):
    folder = os.path.join(ASIDE, time.strftime("%Y%m%d-%H%M%S"))
    for path in paths:
        full = os.path.join(AGENT_HOME, path)
        if os.path.isfile(full) and not os.path.islink(full):
            os.makedirs(os.path.dirname(os.path.join(folder, path)), exist_ok=True)
            shutil.copy2(full, os.path.join(folder, path))
    return folder


def restore(paths):
    set_aside(paths)
    tracked = [p for p in paths if subprocess.run(["git", "-C", AGENT_HOME, "ls-files", "--error-unmatch", p],
                                                   capture_output=True, timeout=30).returncode == 0]
    if tracked:
        subprocess.run(["git", "-C", AGENT_HOME, "checkout", "HEAD", "--", *tracked], capture_output=True, timeout=60)
    for path in set(paths) - set(tracked):
        full = os.path.join(AGENT_HOME, path)
        if os.path.islink(full) or (os.path.lexists(full) and not os.path.isdir(full)):
            os.remove(full)
    return tracked


BACKLOG = os.path.join(AGENT_HOME, "pepper", "backlog.md")
BACKLOG_JOURNAL = os.path.join(AGENT_HOME, "pepper", "state", "backlog.journal.md")


def backlog_drift():
    if not os.path.exists(BACKLOG_JOURNAL):
        return ""
    with open(BACKLOG_JOURNAL) as handle:
        journal = handle.read()
    current = open(BACKLOG).read() if os.path.exists(BACKLOG) else ""
    if current == journal:
        return ""
    folder = set_aside(["pepper/backlog.md"])
    with open(BACKLOG + ".tmp", "w") as handle:
        handle.write(journal)
    os.replace(BACKLOG + ".tmp", BACKLOG)
    return folder
