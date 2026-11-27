#!/usr/bin/env python3
import json
import os
import re
import sys
import unicodedata

PEPPER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
try:
    with open(os.path.join(PEPPER, "config.json")) as _handle:
        _CONFIG = json.load(_handle)
    PREFIXES = tuple([_CONFIG["prefix"]] + _CONFIG.get("prefix_aliases", []))
    # The owner's own places: the Slack workspace, the GitHub orgs and the hosts listed in allowed_link_hosts
    # (each one also covers its subdomains). Any other link is outside.
    OWN_HOSTS = {h.strip().lower().rstrip(".") for h in [_CONFIG["slack_workspace_host"], *_CONFIG.get("allowed_link_hosts", [])]
                 if h.strip()}
    GITHUB_ORGS = {org.lower() for org in _CONFIG.get("github_orgs", []) if org}
except (OSError, ValueError, KeyError) as _failure:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": f"{{AGENT_NAME}}'s send guard has no readable config "
                                                                         f"({_failure}); refusing every send."}}))
    sys.exit(0)
CREDENTIAL = re.compile(
    r"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}"
    r"|mongodb(\+srv)?://[^\s:/@]+:[^\s@]+@"
    r"|\b(AKIA|ASIA)[0-9A-Z]{16}\b"
    r"|\bxox[abposr]-[A-Za-z0-9-]{10,}"
    r"|\bmb_[A-Za-z0-9+/=]{20,}"
    r"|\bgh[pousr]_[A-Za-z0-9]{30,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(client[_-]?secret|api[_-]?key|password|senha)\s*[:=]\s*\S{8,}", re.I)


MASS_MENTION = re.compile(r"<!(channel|here|everyone)(\|[^>]*)?>|<!subteam\^|(^|\s)@(channel|here|everyone)\b", re.I)
PERSON_MENTION = re.compile(r"<@[UW][A-Z0-9]+(\|[^>]*)?>")
MAX_MENTIONS = 3
URL = re.compile(r"\b(?:https?|ftp)://([^\s/|>?#]+)([^\s|>]*)", re.I)
ANY_DOMAIN_WITH_PATH = re.compile(r"(?<![\w@./:-])((?:[a-z0-9-]+\.)+[a-z][a-z0-9-]{1,23})(?=[/\\])", re.I)
BARE_DOMAIN = re.compile(r"(?<![\w@./-])((?:[a-z0-9-]+\.)+(?:com|io|net|org|dev|app|xyz|me|co|br|info|site|online|ru|cn|tk|"
                         r"top|link|sh|ly|gg|to|cc|ai|so|club|live|page|cloud|ngrok-free\.app))(?=/)", re.I)
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
MORE_SECRETS = re.compile(
    r"mongodb(\+srv)?://"
    r"|\barn:aws:[a-z0-9-]*:[a-z0-9-]*:\d{12}:"
    r"|\b(account|conta|account[_ ]id)\D{0,20}\b\d{12}\b"
    r"|\.svc\.cluster\.local\b|\b[\w-]+\.internal\b"
    r"|\b(10\.\d{1,3}|192\.168|172\.(1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b", re.I)
TOKEN_LIKE = re.compile(r"[A-Za-z0-9+/_=-]{32,}")


def entropy(text):
    import math
    counts = {c: text.count(c) for c in set(text)}
    return -sum(n / len(text) * math.log2(n / len(text)) for n in counts.values())


def looks_like_secret(word):
    if re.fullmatch(r"[0-9a-f]+", word, re.I) or not (re.search(r"[A-Za-z]", word) and re.search(r"\d", word)):
        return False
    return entropy(word) >= 4.3


def own_link(host, rest):
    if "@" in host or "\\" in host or "\\" in rest[:1]:
        return False
    host = host.split(":")[0].lower().rstrip(".")
    if host == "github.com":
        import posixpath
        org = posixpath.normpath(rest.split("?")[0] or "/").split("/")[1:2]
        return bool(org) and org[0].lower() in GITHUB_ORGS
    return any(host == own or host.endswith("." + own) for own in OWN_HOSTS)


def outside_links(text):
    text = CODE.sub(" ", text)
    found = [m.group(1) for m in URL.finditer(text) if not own_link(m.group(1), m.group(2))]
    without_urls = URL.sub(" ", text)
    found += [m.group(1) for m in ANY_DOMAIN_WITH_PATH.finditer(without_urls)
              if not own_link(m.group(1), "/" + min(GITHUB_ORGS, default=""))]
    return found


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}))
    sys.exit(0)


def external_channels():
    try:
        with open(os.path.join(PEPPER, "state", "state.json")) as handle:
            return set(json.load(handle).get("external_channels", []))
    except (OSError, ValueError):
        return set()


OUTSIDE_FACING_KINDS = {"bot", "review", "prthreads"}
SEND_TOOLS = {"slack_send_message", "slack_send_message_draft", "slack_schedule_message"}
READ_TOOLS = {"slack_read_thread", "slack_read_channel", "slack_read_user_profile", "slack_read_canvas", "slack_read_file",
              "slack_search_public", "slack_search_users", "slack_search_channels", "slack_search_emojis",
              "slack_list_channel_members", "slack_list_user_channels", "slack_get_reactions",
              "slack_search_public_and_private"}
LOCAL_PATH = re.compile(r"/Users/[A-Za-z]|/home/[a-z]|~/\.|\.ssh/|(^|[\s`'\"(/])\.env\b")
SEXUAL = re.compile(r"\b(sexo|sexual|sexy|sensual\w*|erotic\w*|nudes?|pelad\w*|transar|homossexual|bissexual|lesbica)\b")
INVISIBLE = re.compile("[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")


def pending_approvals():
    try:
        with open(os.path.join(PEPPER, "state", "state.json")) as handle:
            return set(json.load(handle).get("approvals", {}))
    except (OSError, ValueError):
        return set()


def check_other_tool(tool, args):
    kind = os.environ.get("PEPPER_RUN_KIND", "bot")
    control = _CONFIG["control_channel_id"]
    if tool in READ_TOOLS:
        if kind in OUTSIDE_FACING_KINDS and (args.get("channel_id") == control or control in json.dumps(args)
                                             or "{{CONTROL_CHANNEL_NAME}}" in json.dumps(args)):
            deny("A run that answers other people never reads {{OWNER_FIRST_NAME}}'s private channel with {{AGENT_NAME}}.")
        if kind in OUTSIDE_FACING_KINDS and tool == "slack_read_file":
            deny("A run that answers other people never opens an attachment itself: code reads each file in quarantine, "
                 "strips what is hidden and puts the visible content in your prompt between <attachment> tags.")
        if kind in OUTSIDE_FACING_KINDS and tool == "slack_search_public_and_private":
            deny("A run that answers other people searches public channels only (slack_search_public); private "
                 "conversations, DMs and #{{CONTROL_CHANNEL_NAME}} are not its to read. Read the thread you were given instead.")
        return
    if tool == "slack_add_reaction" and args.get("message_ts") in pending_approvals():
        deny("That message waits for {{OWNER_FIRST_NAME}}'s reaction (✅ ❌ ✏️); a reaction from {{AGENT_NAME}} would look like his approval.")
    if tool == "slack_add_reaction":
        allowed = [c for c in os.environ.get("PEPPER_ALLOWED_CHANNELS", "").split(",") if c]
        if os.environ.get("PEPPER_ORDER_RUN") != "1" and allowed and args.get("channel_id") not in allowed:
            deny(f"This run may only react in {', '.join(allowed)}.")
        return
    if tool == "slack_update_canvas" and kind == "calls" and args.get("canvas_id") == _CONFIG.get("panel_canvas_id"):
        return
    if tool in ("slack_update_canvas", "slack_create_canvas") and os.environ.get("PEPPER_ORDER_RUN") == "1":
        return
    deny(f"{tool} is not available to this run (only reading, sending in its own conversation and reacting).")


def main():
    event = json.load(sys.stdin)
    args = event.get("tool_input") or {}
    tool = event.get("tool_name", "mcp__claude_ai_Slack__slack_send_message").split("__")[-1]
    if os.environ.get("PEPPER_RUN_KIND") == "attachment" and tool != "slack_read_file":
        deny("The attachment reader only opens the one file it was given; it reads nothing else and sends nothing.")
    if tool not in SEND_TOOLS:
        check_other_tool(tool, args)
        return
    channel, text = args.get("channel_id", ""), INVISIBLE.sub("", args.get("message", ""))
    if not text.lstrip().startswith(PREFIXES):
        deny(f"Every message starts with '{PREFIXES[0]}' so people know it is the agent, not its owner typing. Add it and resend.")
    if CREDENTIAL.search(text):
        deny("This message looks like it contains a credential (token, key, secret or a URI with a password). "
             "Credentials are never posted on Slack, in any environment. Describe the result instead of pasting it.")
    if MASS_MENTION.search(text) or re.search(r"(^|\s)@\W*(channel|here|everyone)\b", text, re.I):
        deny("{{AGENT_NAME}} never notifies a whole channel or a user group (@channel, @here, @everyone, @group). Mention the "
             "one or two people who need it, or none.")
    order_run = os.environ.get("PEPPER_ORDER_RUN") == "1"
    without_own_urls = URL.sub(lambda m: " " if own_link(m.group(1), m.group(2)) else m.group(0), text)
    if MORE_SECRETS.search(without_own_urls) or any(looks_like_secret(w) for w in TOKEN_LIKE.findall(without_own_urls)):
        deny("This message carries something that looks like a secret or internal infrastructure (a database URI, an "
             "AWS account id or ARN, an internal host or private IP, or a long random string). Describe it instead.")
    outside = outside_links(text)
    if outside and not order_run:
        deny(f"Links go only to {{OWNER_FIRST_NAME}}'s own places (this Slack workspace, the GitHub orgs and hosts in config): "
             f"{', '.join(sorted(set(outside))[:3])} is outside. Slack fetches every link it shows, so a link can carry "
             "data out without a click. Name it without the address, or ask {{OWNER_FIRST_NAME}}. If it is a file path, not a link, "
             "write it inside `backticks`.")
    if outside and order_run and any(m.group(2).find("?") >= 0 for m in URL.finditer(text)
                                     if not own_link(m.group(1), m.group(2))):
        deny("An outside link with a query string can carry data out (Slack fetches it to show a preview). Remove the "
             "query string or describe the link.")
    if not order_run and len({m.group(0).split("|")[0] for m in PERSON_MENTION.finditer(text)}) > MAX_MENTIONS:
        deny(f"At most {MAX_MENTIONS} people are mentioned in one message. Mention only who must act.")
    control = _CONFIG["control_channel_id"]
    if channel != control and (control in text or "{{CONTROL_CHANNEL_NAME}}" in text):
        deny("This message points at #{{CONTROL_CHANNEL_NAME}}, {{OWNER_FIRST_NAME}}'s private channel with {{AGENT_NAME}}. Nothing from it (links, its name, "
             "its ids) goes anywhere else. Remove the reference and resend.")
    if channel != control and LOCAL_PATH.search(text):
        deny("Outside #{{CONTROL_CHANNEL_NAME}} a message never shows a path of this machine (/Users/..., ~/., .ssh/, a .env file): it "
             "maps {{OWNER_FIRST_NAME}}'s machine for whoever reads it. Name the repo path (`pepper/lib/x.py`) or describe it.")
    if channel != control and SEXUAL.search(unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()):
        deny("{{AGENT_NAME}} never posts sexual or intimate content about anyone, outside #{{CONTROL_CHANNEL_NAME}} or anywhere else.")
    if channel in external_channels():
        deny("This is a Slack Connect (external) conversation. {{AGENT_NAME}} never posts there ({{OWNER_FIRST_NAME}}'s rule until a "
             "dedicated skill exists). Tell {{OWNER_FIRST_NAME}} in #{{CONTROL_CHANNEL_NAME}} instead.")
    if os.environ.get("PEPPER_ORDER_RUN") == "1":
        return
    if (_CONFIG.get("draft_only", True) and channel != control
            and os.environ.get("PEPPER_APPROVED_SEND") != "1"):
        deny("Draft-only mode: nothing goes out on its own. Ask {{OWNER_FIRST_NAME}} in #{{CONTROL_CHANNEL_NAME}} with the "
             "draft instead; it is sent only after his ✅.")
    allowed = [c for c in os.environ.get("PEPPER_ALLOWED_CHANNELS", "").split(",") if c]
    if allowed and channel not in allowed:
        deny(f"This run may only post in {', '.join(allowed)} (the conversation it is answering and #{{CONTROL_CHANNEL_NAME}}).")


if __name__ == "__main__":
    try:
        main()
    except Exception as failure:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": f"{{AGENT_NAME}}'s guard failed ({failure}); "
                                                                             "refusing rather than letting it through."}}))
