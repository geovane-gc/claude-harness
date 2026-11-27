#!/usr/bin/env python3
import json
import os
import re
import shlex
import sys

OPERATORS = {";", "&&", "||", "|", "&", "\n", "(", ")", "|&", ";;"}
RISKY_WORDS = re.compile(r"\b(git|gh|bash|sh|zsh|eval|python3?|curl|security|rm)\b")
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELLS = {"bash", "sh", "zsh", "eval", "exec", "source", ".", "xargs", "env", "python", "python3", "perl", "ruby",
          "node", "osascript", "command", "builtin", "nohup", "timeout", "time", "nice", "printenv", "set",
          "declare", "typeset", "export", "compgen", "busybox", "toybox"}

GIT_READ = {"status", "log", "show", "diff", "fetch", "rev-parse", "ls-files", "ls-tree", "cat-file", "blame", "grep",
            "merge-base", "describe", "shortlog", "rev-list", "for-each-ref", "show-ref", "name-rev", "range-diff"}
GIT_GLOBAL_WITH_VALUE = {"-C", "--git-dir", "--work-tree", "--namespace"}
GIT_GLOBAL_FLAGS = {"--no-pager", "-P", "--no-replace-objects", "--literal-pathspecs", "--no-optional-locks"}
GIT_FORBIDDEN_OPTIONS = re.compile(r"^(--upload-pack|--receive-pack|--exec|-u$|--output|-O|--open-files-in-pager|"
                                   r"--ext-diff|--textconv)")

GH_READ = {("pr", "view"), ("pr", "diff"), ("pr", "list"), ("pr", "checks"), ("pr", "status"), ("issue", "view"),
           ("issue", "list"), ("repo", "view"), ("run", "view"), ("run", "list"), ("release", "list"),
           ("release", "view"), ("search", "prs"), ("search", "issues"), ("search", "code"), ("workflow", "list"),
           ("workflow", "view"), ("label", "list"), ("run", "watch"), ("repo", "list"), ("search", "repos"),
           ("issue", "status")}
GH_WRITES = {
    "review": {("pr", "review")},
    "prthreads": {("pr", "comment")},
    "order": {("pr", "comment"), ("pr", "review"), ("pr", "merge"), ("pr", "ready"), ("pr", "edit"),
              ("issue", "comment"), ("issue", "create")},
}
GH_WRITES["answer"] = GH_WRITES["order"]
GH_WRITES["build"] = {("pr", "create"), ("pr", "comment")}
GH_WRITES["prfix"] = {("pr", "comment")}
API_WRITES = {
    "prthreads": [r"^repos/[^/]+/[^/]+/pulls/\d+/comments/\d+/replies$",
                  r"^repos/[^/]+/[^/]+/pulls/\d+/requested_reviewers$"],
    "order": [r"^repos/[^/]+/[^/]+/pulls/\d+/comments/\d+/replies$",
              r"^repos/[^/]+/[^/]+/pulls/\d+/requested_reviewers$",
              r"^repos/[^/]+/[^/]+/(issues|pulls)/\d+/comments$"],
}
API_WRITES["answer"] = API_WRITES["order"]
API_WRITES["build"] = [r"^repos/[^/]+/[^/]+/pulls/\d+/comments/\d+/replies$"]
API_WRITES["prfix"] = API_WRITES["build"]
GRAPHQL_MUTATIONS = {
    "prthreads": {"resolveReviewThread", "addPullRequestReviewThreadReply"},
    "order": {"resolveReviewThread", "addPullRequestReviewThreadReply", "markPullRequestReadyForReview"},
}
GRAPHQL_MUTATIONS["answer"] = GRAPHQL_MUTATIONS["order"]
API_VALUE_FLAGS = {"-H", "--header", "--jq", "-q", "--template", "-t", "--cache", "-p", "--preview"}
GIT_FILE_OPTIONS = re.compile(r"^(--contents|-S$|--ignore-revs-file|-f$|--file|--exclude-from|--exclude-per-directory|"
                              r"--pathspec-from-file|--stdin|--patterns-from|--include-from|--blob)")
REMOTE_ADDRESS = re.compile(r"://|^[\w.-]+@[\w.-]+:|^[\w.-]+::")



AGENT_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
READ_ROOTS = [AGENT_HOME, "/tmp", "/private/tmp"]
OWN_TOOL_RESULTS = re.compile(r"^" + re.escape(os.path.expanduser("~/.claude/projects/")) + r"[^/]*{{HOME_DIR_NAME}}[^/]*/[^/]+/tool-results/[^/]+$")
WRITE_ROOTS = [os.path.join(AGENT_HOME, "knowledge"), "/tmp", "/private/tmp"]
BUILD_WRITE_ROOTS = [AGENT_HOME, "/tmp", "/private/tmp"]
WORKTREES = os.path.join(AGENT_HOME, "worktrees")
REFERENCE_CLONES = os.path.join(AGENT_HOME, "repos")
PROTECTED = [os.path.join(AGENT_HOME, part) for part in (
    "pepper/guard", "pepper/state", "pepper/config.json", "pepper/keep_draft.json", "plugin/hooks", "repos", ".git",
    "bin/secret", "bin/backlog", "knowledge/security-policy.md")]
GIT_BUILD_WRITES = {"add", "commit", "push", "checkout", "switch", "restore", "rm", "mv", "merge", "pull", "stash",
                    "worktree", "branch", "reset", "cherry-pick", "revert"}
STATE = {"kind": "bot"}
AWK_FAMILY = {"awk", "gawk", "mawk", "nawk"}
AGENT_BIN = os.path.join(AGENT_HOME, "bin")
AUDIT_BIN_TOOLS = {"backlog"}
TALK_BIN_TOOLS = {"repos", "access-check", "audience", "pepper-costs", "backlog"}
BUILD_KINDS = {"build", "prfix"}
OUTSIDE_FACING_KINDS = {"bot", "review", "prthreads"}
PRIVATE = [os.path.join(AGENT_HOME, part) for part in (
    "pepper/logs", "pepper/state", "pepper/backlog.md", "pepper/config.json", "pepper/keep_draft.json", "memory",
    "decisions", "board.md", "backup", "research", "knowledge/access.md")]
OUTSIDE_FACING_BIN_TOOLS = {"repos", "audience"}
RECURSIVE_READERS = {"rg", "find"}
TALK_PROGRAMS = {"git", "gh", "echo", "printf", "true", "false", "test", "[", "date", "basename", "dirname", "pwd", "mkdir"}
KEYWORDS_BEFORE_A_COMMAND = {"do", "then", "else", "elif", "if", "while", "until", "!", "{", "}", "time"}
KEYWORDS_WITHOUT_A_COMMAND = {"for", "select", "case", "done", "fi", "esac", "in", "}"}
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n(.*?)(?:\n[ \t]*\2[ \t]*(?=\n|$)|$)", re.S)
FILE_READERS = {"cat", "head", "tail", "grep", "egrep", "rg", "sed", "gsed", "awk", "gawk", "mawk", "nawk", "wc", "ls", "base64", "less", "more",
                "sort", "uniq", "cut", "diff", "find", "jq", "file", "stat", "xxd", "od", "strings", "tr"}


class Refused(Exception):
    pass


def substitutions(text):
    found, position, quote = [], 0, None
    while position < len(text):
        char = text[position]
        if quote == "'":
            if char == "'":
                quote = None
        elif char == "\\":
            position += 1
        elif char == "'" and quote is None:
            quote = "'"
        elif char == '"':
            quote = None if quote == '"' else '"'
        elif text.startswith("$(", position):
            depth, cursor = 1, position + 2
            while cursor < len(text) and depth:
                depth += {"(": 1, ")": -1}.get(text[cursor], 0)
                cursor += 1
            found.append(text[position + 2:cursor - 1])
            position = cursor
            continue
        elif char == "`":
            closing = text.find("`", position + 1)
            closing = len(text) if closing < 0 else closing
            found.append(text[position + 1:closing])
            position = closing + 1
            continue
        position += 1
    return found


def tokenize(text):
    lexer = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


GLOB_CHARS = set("*?[")
VARIABLE = re.compile(r"\$(\{)?([A-Za-z_][A-Za-z0-9_]*)")
SHELL_SPECIAL_VARIABLES = re.compile(r"\$[?#@*0-9!$-]")
PLAIN_BRACED_VARIABLE = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}")


def raw_tokens(text):
    text = text.replace('\\"', "_").replace("\\'", "_")
    lexer = shlex.shlex(text, posix=False, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    lexer.commenters = ""
    return list(lexer)


def unquoted_parts(token):
    expanding, globbing, quote = [], [], None
    for char in token:
        if quote == "'":
            quote = None if char == "'" else quote
            continue
        if char in "'\"" and quote is None:
            quote = char
            continue
        if char == '"' and quote == '"':
            quote = None
            continue
        expanding.append(char)
        globbing.append(char if quote is None else "_")
    return "".join(expanding), "".join(globbing)


def brace_expand(word):
    match = re.search(r"\{([^{}]*,[^{}]*)\}", word)
    if not match:
        return [word]
    return [expanded for option in match.group(1).split(",")
            for expanded in brace_expand(word[:match.start()] + option + word[match.end():])]


def static_prefix(pattern):
    cut = min([pattern.find(c) for c in "*?[{" if c in pattern] or [len(pattern)])
    return pattern[:cut].rsplit("/", 1)[0] if "/" in pattern[:cut] else (pattern[:cut] if cut == len(pattern) else ".")


def check_expanded_path(word, glob_view, directory):
    import glob as globbing
    candidates = brace_expand(word) if "{" in glob_view and "," in glob_view else [word]
    for candidate in candidates:
        if any(c in glob_view for c in GLOB_CHARS) or len(candidates) > 1:
            readable(static_prefix(candidate) or ".", directory)
            for match in globbing.glob(os.path.join(directory, os.path.expanduser(candidate))):
                readable(match, directory)
        if len(candidates) > 1 and os.path.exists(resolve(candidate, directory)):
            readable(candidate, directory)


def check_expansions(command, kind, directory):
    assigned = {}
    current, reads_paths, redirect_next = [], False, False

    def substituted(text):
        return VARIABLE.sub(lambda m: assigned.get(m.group(2), m.group(0)), text).replace("}", "") if "${" in text \
            else VARIABLE.sub(lambda m: assigned.get(m.group(2), m.group(0)), text)

    try:
        tokens = raw_tokens(command)
    except ValueError:
        raise Refused("the command could not be parsed (quotes); write it in a simpler form")
    for token in tokens + [";"]:
        if token in OPERATORS or (token and set(token) <= set(";&|()\n")):
            current, reads_paths, redirect_next = [], False, False
            continue
        if re.match(r"^\d*(>>|>\||>&|&>|>|<)$", token):
            redirect_next = True
            continue
        expanding, glob_view = unquoted_parts(token)
        if not current and ASSIGNMENT.match(expanding):
            name, value = expanding.split("=", 1)
            assigned[name] = substituted(value)
            continue
        if not current and expanding in KEYWORDS_BEFORE_A_COMMAND:
            continue
        if not current and expanding in ("for", "select"):
            current, reads_paths = ["for"], True
            continue
        if current == ["for"] and expanding != "in":
            assigned[expanding] = "."
            current.append(expanding)
            continue
        if not current:
            reads_paths = os.path.basename(expanding) in FILE_READERS or os.path.basename(expanding) in ("git", "gh")
        current.append(expanding)
        if len(current) == 1 and not redirect_next:
            continue
        if not (reads_paths or redirect_next):
            continue
        redirect_next = False
        for name in (m.group(2) for m in VARIABLE.finditer(SHELL_SPECIAL_VARIABLES.sub("", expanding))):
            if name not in assigned:
                raise Refused(f"${name} is not set in this command; write the path itself instead of a variable")
        if expanding.startswith("-") or expanding == "in":
            continue
        if VARIABLE.search(expanding):
            expanding = substituted(expanding)
            glob_view = expanding
            if os.path.exists(resolve(expanding, directory)):
                readable(expanding, directory)
        check_expanded_path(expanding, glob_view, directory)


def segments(command):
    pending = [(command, True)]
    while pending:
        text, top_level = pending.pop()
        pending.extend((inner, False) for inner in substitutions(text))
        try:
            tokens = tokenize(text)
        except ValueError:
            if top_level or RISKY_WORDS.search(text):
                raise Refused("the command could not be parsed (unbalanced quotes)")
            continue
        current = []
        for token in tokens:
            if token in OPERATORS or (token and set(token) <= set(";&|()\n")):
                if current:
                    yield current
                current = []
            else:
                current.append(token)
        if current:
            yield current


def resolve(path, directory):
    return os.path.realpath(os.path.join(directory, os.path.expanduser(path)))


def inside(path, roots):
    return any(path == root or path.startswith(root.rstrip("/") + "/") for root in roots)


def readable(path, directory):
    resolved = resolve(path, directory)
    if OWN_TOOL_RESULTS.match(resolved):
        return
    if not inside(resolved, READ_ROOTS):
        raise Refused(f"{path} is outside what a run may read (the agent folder and /tmp)")
    if STATE["kind"] in OUTSIDE_FACING_KINDS and inside(resolved, PRIVATE):
        raise Refused(f"{path} holds {{OWNER_FIRST_NAME}}'s private conversations or plans; a run that answers other people never reads it")


def private_below(path, directory):
    resolved = resolve(path, directory)
    reachable = [p for p in PRIVATE if not inside(p, [os.path.join(AGENT_HOME, "knowledge")])]
    return any(inside(private, [resolved]) for private in reachable)


def check_recursive_read(name, args, directory):
    if STATE["kind"] not in OUTSIDE_FACING_KINDS:
        return
    recursive = name in RECURSIVE_READERS or (name in ("grep", "egrep") and any(
        a.startswith("-") and not a.startswith("--") and ("r" in a or "R" in a) or a in ("--recursive", "--dereference-recursive")
        for a in args))
    if not recursive:
        return
    positional = [a for a in args if not a.startswith("-")]
    if name == "find":
        targets = []
        for arg in args:
            if arg.startswith(("-", "(", "!")):
                break
            targets.append(arg)
    else:
        targets = positional[1:]
    targets = targets or ["."]
    for target in targets:
        if private_below(target, directory):
            raise Refused(f"a recursive read of {target} reaches {{OWNER_FIRST_NAME}}'s private files (logs, state, backlog, memory); "
                          "search knowledge/, pepper/skills or repos/<repo> instead")


def writable(path, directory):
    if path in ("/dev/null", "&1", "&2", "1", "2"):
        return
    resolved = resolve(path, directory)
    if STATE["kind"] == "prfix":
        if not inside(resolved, [WORKTREES, "/tmp", "/private/tmp"]):
            raise Refused(f"a fix run writes only inside its worktree and /tmp, not {path}")
        return
    if STATE["kind"] in BUILD_KINDS:
        if inside(resolved, PROTECTED) and not inside(resolved, [WORKTREES]):
            raise Refused(f"{path} is protected: guards, secrets, policies, state and reference clones change only "
                          "in a session with {{OWNER_FIRST_NAME}}")
        if not inside(resolved, BUILD_WRITE_ROOTS):
            raise Refused(f"writing to {path} is not allowed (only the agent folder, its worktrees and /tmp)")
        return
    agent_but_not_knowledge = inside(resolved, [AGENT_HOME]) and not inside(resolved, WRITE_ROOTS[:1])
    if agent_but_not_knowledge or not inside(resolved, WRITE_ROOTS):
        raise Refused(f"writing to {path} is not allowed (only knowledge/ and /tmp)")


def strip_redirections(words, directory):
    result, target_of = [], None
    for word in words:
        if target_of:
            (writable if ">" in target_of else readable)(word, directory)
            target_of = None
            continue
        match = re.match(r"^(\d*)(>>|>\||>&|&>|>|<<<|<<|<)(.*)$", word)
        if match:
            operator, rest = match.group(2), match.group(3)
            if operator in ("<<", "<<<"):
                continue
            if rest:
                (writable if ">" in operator else readable)(rest, directory)
            else:
                target_of = operator
            continue
        result.append(word)
    return result


SED_ADDRESS = r"(\d+|\$|/[^/]*/)"
SED_COMMAND = re.compile(r"\s*(" + SED_ADDRESS + r"(\s*,\s*" + SED_ADDRESS + r")?)?\s*!?\s*"
                         r"(p|d|q|=|s(.).*\6.*\6[gpI0-9]*)\s*", re.S)
FIND_ACTIONS = re.compile(r"^-(exec|execdir|ok|okdir|delete|fprint|fprint0|fprintf|fls)$")
AWK_RISKY = re.compile(r"system|getline|\||>|ENVIRON")
SECRET_REFERENCE = re.compile(r"\$\{?[A-Za-z_]*(TOKEN|SECRET|PASSWORD|KEY)[A-Za-z_]*", re.I)
SINGLE_QUOTED = re.compile(r"'[^']*'")


def check_program_flags(name, args):
    if name == "find" and any(FIND_ACTIONS.match(arg) for arg in args):
        raise Refused("find may only list files here (no -exec, -ok, -delete or -fprint)")
    if name in AWK_FAMILY:
        if any(arg in ("-f", "--file") or arg.startswith("-f") for arg in args):
            raise Refused("awk programs from a file are not allowed")
        if any(AWK_RISKY.search(arg) for arg in args):
            raise Refused("awk may only filter text here (no system, getline, pipes, redirects or ENVIRON)")
    if name in ("sed", "gsed"):
        if any(arg in ("-f", "--file") or arg.startswith(("-f", "--file=")) for arg in args):
            raise Refused("sed scripts from a file are not allowed")
        scripts = [args[i + 1] for i, arg in enumerate(args) if arg in ("-e", "--expression") and i + 1 < len(args)]
        if not scripts:
            remaining, position = [], 0
            while position < len(args):
                if args[position] == "-i":
                    position += 2
                    continue
                if not args[position].startswith("-"):
                    remaining.append(args[position])
                position += 1
            scripts = remaining[:1]
        for script in scripts:
            for piece in re.split(r"[;\n]", script):
                if piece.strip() and not SED_COMMAND.fullmatch(piece):
                    raise Refused("sed may only print, delete or substitute here (no e, w, r or other commands)")


PATTERN_FIRST = {"grep", "egrep", "rg", "awk", "gawk", "mawk", "nawk", "sed", "gsed", "jq", "tr"}


def path_arguments(name, args):
    positional = [a for a in args if not a.startswith("-")]
    if name in PATTERN_FIRST and not any(a in ("-e", "-f", "--regexp", "--file") or a.startswith(("-e", "--regexp="))
                                         for a in args):
        return positional[1:]
    if name == "tr":
        return []
    return positional


def looks_like_path(value):
    return value.startswith(("/", "~", "./", "../")) or "/" in value or value in (".", "..")


def option_values(arg):
    values = [arg]
    if arg.startswith("--"):
        if "=" in arg:
            values.append(arg.split("=", 1)[1])
    elif re.match(r"^-[A-Za-z]", arg):
        if "=" in arg:
            values.append(arg.split("=", 1)[1])
        for position in range(2, len(arg)):
            values.append(arg[position:])
            if arg[position] == "=":
                values.append(arg[position + 1:])
            if not arg[position].isalnum():
                break
    return values


def check_paths(name, args, directory):
    for value in path_arguments(name, args):
        if looks_like_path(value):
            readable(value, directory)
    if name == "sed" and any(a == "-i" or a.startswith(("-i", "--in-place")) for a in args):
        for arg in args:
            if not arg.startswith("-") and ("/" in arg or "." in arg) and os.path.exists(resolve(arg, directory)):
                writable(arg, directory)
    for arg in args:
        for value in option_values(arg):
            if value and not value.startswith("-") and os.path.exists(resolve(value, directory)):
                readable(value, directory)


def program(words):
    prefixed = bool(words) and bool(ASSIGNMENT.match(words[0])) and any(not ASSIGNMENT.match(w) for w in words)
    if prefixed and STATE["kind"] not in BUILD_KINDS:
        raise Refused("a variable set in front of a command (VAR=x cmd) is not allowed here; it can redirect git, gh "
                      "or a pager to another config or program")
    while words and ASSIGNMENT.match(words[0]):
        name = words[0].split("=", 1)[0]
        if name in ("GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_SSH_COMMAND", "GIT_EXTERNAL_DIFF",
                    "GIT_PAGER", "PAGER", "GH_PAGER", "AWS_PROFILE", "AWS_DEFAULT_PROFILE", "GH_TOKEN", "GITHUB_TOKEN"):
            raise Refused(f"setting {name} on the command line is not allowed")
        words = words[1:]
    return words


def check_git_build(subcommand, rest, target):
    in_worktree = inside(target, [WORKTREES])
    in_agent_repo = (inside(target, [AGENT_HOME]) and not inside(target, [REFERENCE_CLONES, WORKTREES])
                     and STATE["kind"] == "build")
    if subcommand == "worktree":
        if rest[:1] == ["add"]:
            paths = [a for a in rest[1:] if not a.startswith("-")]
            if not paths or not inside(resolve(paths[0], target), [WORKTREES]):
                raise Refused(f"new worktrees go under {WORKTREES}/<repo>/<branch>")
            return
        if rest[:1] in (["list"], ["prune"], ["remove"]):
            return
        raise Refused(f"git worktree {' '.join(rest[:1])} is not allowed")
    if not (in_worktree or in_agent_repo):
        raise Refused(f"git {subcommand} writes only in the agent folder or a worktree under {WORKTREES}; "
                      "the reference clones in repos/ stay read-only")
    if subcommand == "push":
        if any(re.match(r"^(-f|--force.*|--mirror|--all|--tags|--delete|-d|--prune|-[a-zA-Z]*f[a-zA-Z]*)$", a)
               for a in rest):
            raise Refused("push without force, delete, mirror or tags")
        specs = [a for a in rest if not a.startswith("-")][1:]
        if not specs or any(spec.startswith("+") or spec.split(":")[-1].replace("refs/heads/", "") in ("main", "master")
                            or spec.startswith(":") for spec in specs):
            raise Refused("push names one feature branch explicitly (git push -u origin <branch>), never main or master")
        if in_agent_repo:
            raise Refused("the agent folder is committed locally, never pushed")
        return
    if subcommand in ("add", "commit", "rm", "mv", "restore", "checkout", "stash") and in_agent_repo:
        for arg in rest:
            if not arg.startswith("-") and inside(resolve(arg, target), PROTECTED):
                raise Refused(f"{arg} is protected: guards, secrets, policies and config change only in a session with {{OWNER_FIRST_NAME}}")
        if subcommand in ("add", "commit") and any(a in ("-a", "--all", "-A", ".") for a in rest):
            raise Refused("name the files you commit in the agent folder (never -a, -A or .)")
    if subcommand == "reset" and any(a in ("--hard", "--merge", "--keep") for a in rest):
        raise Refused("git reset --hard is not allowed; use git restore or a new commit")
    if subcommand in ("checkout", "switch") and any(a in ("-f", "--force", "--discard-changes", "-B", "-C") for a in rest):
        raise Refused(f"git {subcommand} with force is not allowed")
    if subcommand == "branch" and any(a in ("-D", "-f", "--force", "-M", "-C") for a in rest):
        raise Refused("git branch with force is not allowed")


def check_git(args, directory=None):
    target = directory or os.getcwd()
    position = 0
    while position < len(args) and args[position].startswith("-"):
        option = args[position]
        if option == "-c" and STATE["kind"] in BUILD_KINDS and position + 1 < len(args) and re.match(
                r"^user\.(name|email)=[^!$`;|&]*$", args[position + 1]):
            position += 2
        elif option == "-C" and position + 1 < len(args):
            target = resolve(args[position + 1], target)
            position += 2
        elif option in GIT_GLOBAL_WITH_VALUE:
            if option in ("--git-dir", "--work-tree") and position + 1 < len(args) and STATE["kind"] not in BUILD_KINDS:
                readable(args[position + 1], target)
            position += 2
        elif option.startswith(("--git-dir=", "--work-tree=")):
            if STATE["kind"] not in BUILD_KINDS:
                readable(option.split("=", 1)[1], target)
            position += 1
        elif option in GIT_GLOBAL_FLAGS:
            position += 1
        else:
            raise Refused(f"git option {option} is not allowed (only -C, --no-pager and the like)")
    if STATE["kind"] not in BUILD_KINDS:
        try:
            readable(target, directory or os.getcwd())
        except Refused as refused:
            raise Refused(f"{refused}; read code from the clone ~/{{HOME_DIR_NAME}}/repos/<repo> "
                          "(bin/repos sync <repo> if it is missing)")
    if position >= len(args):
        return
    subcommand, rest = args[position], args[position + 1:]
    for option in rest:
        if option == "-u" and subcommand in ("push", "branch"):
            continue
        if GIT_FORBIDDEN_OPTIONS.match(option):
            raise Refused(f"git {subcommand} {option} is not allowed (it can run a program or write a file)")
    if STATE["kind"] in BUILD_KINDS:
        for option in rest:
            if GIT_FILE_OPTIONS.match(option) and not (subcommand in ("commit", "tag") and option.startswith(("--file", "-F"))):
                raise Refused(f"git {subcommand} {option} reads a file named on the command line")
            for value in option_values(option):
                if looks_like_path(value):
                    readable(value, target)
    if STATE["kind"] in BUILD_KINDS and subcommand in GIT_BUILD_WRITES:
        check_git_build(subcommand, rest, target)
        return
    if subcommand == "branch":
        if any(a in ("-d", "-D", "-m", "-M", "-c", "-C", "-f", "-u", "--delete", "--move", "--copy", "--force",
                     "--edit-description", "--unset-upstream") or a.startswith("--set-upstream") for a in rest):
            raise Refused("git branch may only list branches here")
        if [a for a in rest if not a.startswith("-")] and not any(
                a.startswith(("--list", "--contains", "--merged", "--no-merged", "--points-at")) for a in rest):
            raise Refused("git branch may only list branches here")
        return
    if subcommand == "remote" and (not rest or rest[0] in ("-v", "show", "get-url")):
        return
    if subcommand == "worktree" and rest[:1] == ["list"]:
        return
    if subcommand not in GIT_READ:
        raise Refused(f"git {subcommand} is not allowed here; runs only read git (status, log, show, diff, fetch...)")
    for option in rest:
        if GIT_FILE_OPTIONS.match(option):
            raise Refused(f"git {subcommand} {option} reads a file named on the command line; not allowed here")
        if subcommand in ("fetch", "ls-remote", "pull") and REMOTE_ADDRESS.search(option):
            raise Refused(f"git {subcommand} may only talk to the clone's own remote (origin), not {option[:60]}")
        check_argument_path(option, target)
    if "--no-index" in rest:
        raise Refused("git diff --no-index reads files outside the repository")
    for option in rest:
        if GIT_FORBIDDEN_OPTIONS.match(option):
            raise Refused(f"git {subcommand} {option} is not allowed (it can run a program or write a file)")


def field_value(arg, following):
    for flag in ("--raw-field", "--field", "--input"):
        if arg == flag:
            return True, following
        if arg.startswith(flag + "="):
            return True, arg.split("=", 1)[1]
    if arg in ("-f", "-F"):
        return True, following
    if arg.startswith(("-f", "-F")) and len(arg) > 2:
        return True, arg[2:]
    return False, None


def api_arguments(args):
    method, endpoint, fields, position = None, None, [], 0
    while position < len(args):
        arg = args[position]
        following = args[position + 1] if position + 1 < len(args) else ""
        is_field, value = field_value(arg, following)
        if is_field:
            fields.append((arg, value or ""))
            position += 1 if "=" in arg or (arg.startswith(("-f", "-F")) and len(arg) > 2) else 2
            continue
        if arg in ("-X", "--method"):
            method, position = following.upper(), position + 2
            continue
        if arg.startswith("--method="):
            method = arg.split("=", 1)[1].upper()
        elif arg.startswith("-X"):
            method = arg[2:].upper()
        elif arg in API_VALUE_FLAGS:
            position += 2
            continue
        elif arg.startswith("-") and not arg.startswith(tuple(f + "=" for f in API_VALUE_FLAGS if f.startswith("--"))) \
                and arg not in ("--paginate", "--slurp", "--include", "-i", "--silent", "--verbose"):
            raise Refused(f"gh api option {arg} is not known to the guard")
        elif not arg.startswith("-") and endpoint is None:
            endpoint = arg
        position += 1
    return (method or ("POST" if fields else "GET")), endpoint or "", fields


def top_level_fields(operation_body):
    names, depth, position = [], 0, 0
    while position < len(operation_body):
        char = operation_body[position]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        elif char == "(" and depth >= 1:
            closing, inner = position, 0
            while closing < len(operation_body):
                inner += {"(": 1, ")": -1}.get(operation_body[closing], 0)
                if inner == 0:
                    break
                closing += 1
            position = closing
        elif depth == 1 and (char.isalpha() or char == "_"):
            match = re.match(r"[A-Za-z_]\w*", operation_body[position:])
            names.append(match.group(0))
            position += len(match.group(0))
            continue
        position += 1
    return names


def check_graphql(fields, kind):
    if any(flag.startswith("--input") for flag, _ in fields):
        raise Refused("gh api graphql --input hides the query; pass it with -f query=...")
    queries = [value[len("query="):] for _, value in fields if value.startswith("query=")]
    others = [value.split("=", 1)[0] for _, value in fields if not value.startswith("query=")]
    if len(queries) != 1 or any(q.startswith("@") for q in queries):
        raise Refused("gh api graphql needs exactly one inline -f query=...")
    if "operationName" in others:
        raise Refused("gh api graphql with operationName is not allowed; send one operation")
    if not re.search(r"(mutation|subscription)", queries[0], re.I):
        return
    query = re.sub(r"#[^\n]*", "", queries[0].replace("\\n", "\n")).replace(",", " ")
    match = re.fullmatch(r"\s*mutation\s*(\w+\s*)?(\{.*\})\s*", query, re.S)
    if not match or len(re.findall(r"\b(mutation|query|subscription)\b", query)) != 1:
        raise Refused("a graphql mutation must be the only operation in the query")
    names = set(top_level_fields(match.group(2)))
    allowed = GRAPHQL_MUTATIONS.get(kind, set())
    if not names or not names <= allowed:
        raise Refused(f"graphql mutation {', '.join(sorted(names)) or '?'} is not allowed in a {kind} run")


def check_gh_api(args, kind):
    method, endpoint, fields = api_arguments(args)
    endpoint = endpoint.lstrip("/").split("?")[0]
    if os.environ.get("PEPPER_NO_APPROVE") == "1" and any("APPROVE" in str(value).upper() for _, value in fields):
        raise Refused("this PR carries text aimed at automated reviewers; {{AGENT_NAME}} does not approve it")
    if endpoint == "graphql":
        check_graphql(fields, kind)
        return
    if method == "GET":
        return
    if method == "POST" and any(re.match(p, endpoint) for p in API_WRITES.get(kind, [])):
        return
    raise Refused(f"gh api {method} {endpoint} is not allowed in a {kind} run")


MERGEABLE_STATES = {"CLEAN", "HAS_HOOKS"}


def merge_target(args):
    repo, number, position = "", "", 0
    words = []
    while position < len(args):
        arg = args[position]
        if arg in ("-R", "--repo") and position + 1 < len(args):
            repo, position = args[position + 1], position + 2
            continue
        if arg.startswith("--repo="):
            repo = arg.split("=", 1)[1]
        elif not arg.startswith("-"):
            words.append(arg)
        position += 1
    candidates = [w for w in words[2:] if re.match(r"^(\d+|https://github\.com/[\w.-]+/[\w.-]+/pull/\d+)$", w)]
    if candidates:
        link = re.match(r"^https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)$", candidates[0])
        repo, number = (link.group(1), link.group(2)) if link else (repo, candidates[0])
    return repo, number


def check_merge_ready(args):
    import subprocess
    repo, number = merge_target(args)
    if not repo or not number:
        raise Refused("gh pr merge needs the PR number and -R owner/repo, so the guard can check it first")
    import time
    view = {}
    for attempt in range(2):
        done = subprocess.run(["gh", "pr", "view", number, "-R", repo, "--json", "reviewDecision,mergeStateStatus,isDraft"],
                              capture_output=True, text=True, timeout=25)
        try:
            view = json.loads(done.stdout)
        except ValueError:
            raise Refused(f"could not read {repo}#{number} to check it before merging")
        if view.get("mergeStateStatus") != "UNKNOWN":
            break
        time.sleep(4)
    if view.get("isDraft") or view.get("reviewDecision") != "APPROVED" or view.get("mergeStateStatus") not in MERGEABLE_STATES:
        raise Refused(f"{repo}#{number} is not ready to merge (review {view.get('reviewDecision')}, state "
                      f"{view.get('mergeStateStatus')}, draft {view.get('isDraft')}); tell {{OWNER_FIRST_NAME}} why instead")


def check_argument_path(arg, directory):
    for candidate in option_values(arg) if arg.startswith("-") else [arg]:
        candidate = candidate.split("=", 1)[1] if re.match(r"^[\w.-]+=@", candidate) else candidate
        candidate = candidate.lstrip("@")
        if candidate and not candidate.startswith("-") and os.path.exists(resolve(candidate, directory)):
            readable(candidate, directory)


def check_gh(args, kind, directory=None):
    words = [a for a in args if not a.startswith("-")]
    if words[:2] == ["auth", "status"]:
        if len(args) > 2:
            raise Refused("only a bare `gh auth status` is allowed (its flags can print the token)")
        return
    for position, arg in enumerate(args):
        if arg in ("--hostname", "-R", "--repo") or arg.startswith(("--hostname=", "--repo=")):
            value = arg.split("=", 1)[1] if "=" in arg else (args[position + 1] if position + 1 < len(args) else "")
            if arg.startswith("--hostname") or value.count("/") > 1 or "." in value.split("/")[0]:
                raise Refused("gh talks only to github.com here (no --hostname, no HOST/OWNER/REPO)")
        if arg == "--input" or arg.startswith("--input="):
            raise Refused("gh --input sends a local file; not allowed here")
        if re.match(r"^(-[fF]|--field=|--raw-field=)?[\w.\[\]-]*=@", arg) or (
                position > 0 and args[position - 1] in ("-f", "-F", "--field", "--raw-field") and "=@" in arg):
            value = arg.split("=@", 1)[1]
            readable(value, directory or os.getcwd())
            if STATE["kind"] in OUTSIDE_FACING_KINDS:
                raise Refused("a field read from a file (=@path) is not allowed in a run that answers other people")
        check_argument_path(arg, directory or os.getcwd())
    if words[:2] == ["pr", "merge"]:
        check_merge_ready(args)
    if os.environ.get("PEPPER_NO_APPROVE") == "1" and words[:2] == ["pr", "review"] and any(
            a.startswith("--approve") or re.match(r"^-[A-Za-z]*a[A-Za-z]*$", a) for a in args):
        raise Refused("this PR carries text aimed at automated reviewers; {{AGENT_NAME}} does not approve it")
    if not words:
        return
    if words[0] == "api":
        check_gh_api(args[args.index("api") + 1:], kind)
        return
    pair = tuple(words[:2])
    if os.environ.get("PEPPER_NO_APPROVE") == "1" and pair == ("pr", "review") and any(
            a in ("--approve", "-a") for a in args):
        raise Refused("this PR carries text aimed at automated reviewers; {{AGENT_NAME}} does not approve it (comment or "
                      "request changes, and name the file and line)")
    if pair == ("pr", "create") and kind in BUILD_KINDS and "--draft" not in args and "-d" not in args:
        raise Refused("a build run opens PRs only as drafts (gh pr create --draft)")
    if pair in GH_READ or pair in GH_WRITES.get(kind, set()):
        return
    raise Refused(f"gh {' '.join(pair)} is not allowed in a {kind} run")


AUDIT_SCRIPTS = [os.path.join(AGENT_HOME, "pepper", "guard", name) for name in
                 ("bash_guard.py", "read_guard.py", "slack_send_guard.py")]


def python_allowed_in_audit(args, directory):
    args = [a for a in args if a not in ("-I", "-B")]
    if args[:2] == ["-m", "unittest"]:
        return all(not a.startswith("-") and a.endswith(".py") and inside(resolve(a, directory), [os.path.join(AGENT_HOME, "pepper")])
                   for a in args[2:])
    return len(args) == 1 and resolve(args[0], directory) in AUDIT_SCRIPTS


def python_allowed_in_build(args, directory):
    args = [a for a in args if a not in ("-I", "-B", "-u", "-E", "-s")]
    if args[:2] in (["-m", "unittest"], ["-m", "py_compile"], ["-m", "pytest"]):
        return True
    if not args or args[0].startswith("-"):
        return False
    script = resolve(args[0], directory)
    if script == os.path.join(AGENT_HOME, "pepper", "watch.py"):
        return "--dry" in args
    if os.path.basename(script).startswith("test_") and inside(script, [os.path.join(AGENT_HOME, "pepper")]):
        return os.path.isfile(script) and not inside(script, PROTECTED)
    return script.endswith(".py") and os.path.isfile(script) and inside(script, [WORKTREES]) and not inside(script, PROTECTED)


def heredoc_body(match):
    head = match.group(0)[:match.start(3) - match.start(0)]
    if match.group(1):
        return head
    return head + "\n".join(f'echo "$({inner})"' for inner in substitutions(match.group(3)))


def without_keywords(words):
    while words and words[0] in KEYWORDS_BEFORE_A_COMMAND:
        words = words[1:]
    return [] if words and words[0] in KEYWORDS_WITHOUT_A_COMMAND else words


def check_known_program(word, kind, directory):
    name = os.path.basename(word)
    if kind in BUILD_KINDS or (kind == "audit" and name in ("python3", "python")):
        return
    if "/" in word or word.startswith("~"):
        tools = (OUTSIDE_FACING_BIN_TOOLS if kind in OUTSIDE_FACING_KINDS
                 else AUDIT_BIN_TOOLS | {"repos"} if kind == "audit" else TALK_BIN_TOOLS)
        if os.path.dirname(resolve(word, directory)) == os.path.realpath(AGENT_BIN) and name in tools:
            return
        raise Refused(f"{word} is not one of {{AGENT_NAME}}'s tools")
    if name not in TALK_PROGRAMS and name not in FILE_READERS:
        raise Refused(f"{name} is not on the list of programs a {kind} run may use")


def shell_only_form(command):
    quote, previous = None, " "
    for position, char in enumerate(command):
        following = command[position + 1:position + 3]
        if quote == "'":
            quote = None if char == "'" else quote
        elif char == "\\":
            pass
        elif quote is None and char == "$" and following[:1] in ("'", '"'):
            return True
        elif quote != "'" and char == "$" and following[:1] == "{" and not PLAIN_BRACED_VARIABLE.match(command, position):
            return True
        elif quote is None and char == "~" and previous in " \t\n=:;|&(<>" and following[:1] in ("+", "-") + tuple("0123456789"):
            return True
        elif char in "'\"" and quote is None:
            quote = char
        elif char == '"' and quote == '"':
            quote = None
        previous = char
    return False


def check(command, kind, directory=None):
    STATE["kind"] = kind
    directory = directory or os.getcwd()
    if SECRET_REFERENCE.search(SINGLE_QUOTED.sub("", command)):
        raise Refused("commands may not read token, secret or key variables")
    command = HEREDOC.sub(heredoc_body, command)
    if shell_only_form(command):
        raise Refused("$'...', $\"...\", ${name:-x} and other ${...} operators, ${!name} and ~+ / ~- / ~N expand in the "
                      "shell differently from what the guard checks; write the plain text, path or ${name} instead")
    check_expansions(command, kind, directory)
    for words in segments(command):
        words = without_keywords(program(strip_redirections(words, directory)))
        if not words or (len(words) == 1 and words[0].isdigit()):
            continue
        name = os.path.basename(words[0])
        if name == "cd":
            directory = resolve(words[1] if len(words) > 1 else "~", directory)
            continue
        check_known_program(words[0], kind, directory)
        if name == "mkdir" and kind not in BUILD_KINDS:
            for target in (w for w in words[1:] if not w.startswith("-")):
                writable(target, directory)
        if name in FILE_READERS:
            check_recursive_read(name, words[1:], directory)
            check_program_flags(name, words[1:])
            check_paths(name, words[1:], directory)
        if kind in BUILD_KINDS and name in ("python3", "python") and python_allowed_in_build(words[1:], directory):
            continue
        if kind == "audit" and name in ("python3", "python") and python_allowed_in_audit(words[1:], directory):
            continue
        if name in SHELLS:
            raise Refused(f"{name} runs another command and is not allowed here")
        if name == "git":
            check_git(words[1:], directory)
        elif name == "gh":
            check_gh(words[1:], kind, directory)


def main():
    event = json.load(sys.stdin)
    command = event.get("tool_input", {}).get("command", "")
    kind = os.environ.get("PEPPER_RUN_KIND", "bot")
    try:
        check(command, kind, event.get("cwd") or os.getcwd())
    except Exception as refused:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"Refused by {{AGENT_NAME}}'s command guard: {refused}."}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as failure:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"{{AGENT_NAME}}'s command guard failed ({failure}); "
                                                                             "refusing rather than letting it through."}}))
