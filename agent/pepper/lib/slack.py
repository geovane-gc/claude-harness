import json
import re
import urllib.parse

from .settings import AGENT_NAME, CONFIG, OWNER, SLACK_URL

SEARCH = "slack_search_public_and_private"
RESULT_SPLIT = re.compile(r"^### Result \d+ of \d+\n", re.M)
FIELD = re.compile(r"^(Channel|From|Message_ts|Permalink): (.*)$", re.M)
ID = re.compile(r"\(ID: ([A-Z0-9]+)\)")


def search(keywords, after, **extra):
    args = {"after": str(int(after)), "sort": "timestamp", "sort_dir": "desc", "include_context": False, "limit": 20}
    if keywords:
        args["keywords"] = keywords
    args.update(extra)
    return {"tool": SEARCH, "args": args}


NAMES = (AGENT_NAME, "{{OWNER_FIRST_NAME}}")


def scan_calls(after):
    calls = [search([], after, filters="is:dm", channel_types="im,mpim"),
             search([f"<@{OWNER}>"], after)]
    calls += [search([name], after) for name in NAMES]
    calls.append(search([], after, filters=f"from:<@{OWNER}>", channel_types="public_channel,private_channel"))
    calls += [search([f"<@{group}>"], after) for group in CONFIG["user_groups"].values()]
    calls += [search(["github.com"], after, filters=f"in:<#{channel}>", include_bots=True)
              for channel in CONFIG["watched_channels"].values()]
    calls.append(search([], after, filters=f"in:<#{CONFIG['control_channel_id']}> from:<@{OWNER}>"))
    return calls


def thread_call(channel, thread_ts):
    return {"tool": "slack_read_thread", "args": {"channel_id": channel, "message_ts": thread_ts}}


def parse_search(text):
    try:
        body = json.loads(text).get("results", "")
    except ValueError:
        body = text
    messages = []
    for chunk in RESULT_SPLIT.split(body)[1:]:
        fields = dict(FIELD.findall(chunk))
        channel_ids, author_ids = ID.findall(fields.get("Channel", "")), ID.findall(fields.get("From", ""))
        link = re.search(r"\((https://[^)]+)\)", fields.get("Permalink", ""))
        permalink = link.group(1).replace("\\/", "/") if link else ""
        thread = urllib.parse.parse_qs(urllib.parse.urlparse(permalink).query).get("thread_ts", [""])[0]
        text_part = chunk.split("\nText: \n", 1)[1] if "\nText: \n" in chunk else ""
        ts = fields.get("Message_ts", "").strip()
        messages.append({
            "channel": channel_ids[0] if channel_ids else "",
            "channel_label": fields.get("Channel", "").split(" (ID")[0],
            "user": author_ids[0] if author_ids else "",
            "bot": "[BOT]" in fields.get("From", ""),
            "ts": ts,
            "thread_ts": thread if thread and thread != ts else "",
            "permalink": permalink,
            "text": text_part.rsplit("\n\n---", 1)[0].strip(),
        })
    return messages


def parse_thread_root(text):
    try:
        body = json.loads(text).get("messages", "")
    except ValueError:
        body = text
    parent = body.split("=== THREAD REPLIES", 1)[0]
    return parent.split("=== THREAD PARENT MESSAGE ===", 1)[-1]


CLAUDE_FOOTER = re.compile(r"^(?:>|&gt;)?\s?\*[^*\n]{3,60}\*\s*<@" + CONFIG["claude_app_user_id"] + r"\|Claude>", re.M)
BLOCK = re.compile(r"^(?:=== THREAD PARENT MESSAGE ===|--- Reply \d+ of \d+ ---)\s*$", re.M)


def parse_thread_messages(text):
    try:
        body = json.loads(text).get("messages", "")
    except ValueError:
        body = text
    found = []
    for chunk in BLOCK.split(body.split("=== THREAD REPLIES", 1)[0] + "\n" + "".join(body.split("=== THREAD REPLIES", 1)[1:])):
        ts = re.search(r"^Message TS:\s*(\d+\.\d+)", chunk, re.M)
        if ts:
            found.append({"ts": ts.group(1), "text": chunk, "sent_using_claude": bool(CLAUDE_FOOTER.search(chunk))})
    return found


def parse_thread_replies(text, channel, thread_ts):
    messages = []
    for found in parse_thread_messages(text):
        if found["ts"] == thread_ts:
            continue
        chunk = found["text"]
        author = ID.findall(next((line for line in chunk.splitlines() if line.startswith(("From:", "User:", "Author:"))), ""))
        body = chunk.split("\nText:", 1)[1].strip() if "\nText:" in chunk else chunk.strip()
        link = f"{SLACK_URL}archives/{channel}/p{found['ts'].replace('.', '')}?thread_ts={thread_ts}&cid={channel}"
        messages.append({"channel": channel, "channel_label": "", "user": author[0] if author else "", "bot": False,
                         "ts": found["ts"], "thread_ts": thread_ts, "permalink": link, "text": body, "sources": ["thread"]})
    return messages


def send_call(channel, thread_ts, message, broadcast=False):
    args = {"channel_id": channel, "message": message}
    if thread_ts:
        args["thread_ts"] = thread_ts
        if broadcast:
            args["reply_broadcast"] = True
    return {"tool": "slack_send_message", "args": args}


def reaction_call(channel, ts, emoji):
    return {"tool": "slack_add_reaction", "args": {"channel_id": channel, "message_ts": ts, "emoji": emoji}}


def sent_ts(text):
    match = re.search(r'message_ts\\?"?\s*[:=]\s*\\?"?(\d+\.\d+)', text)
    if match:
        return match.group(1)
    link = re.search(r"/p(\d{10})(\d{6})", text)
    return f"{link.group(1)}.{link.group(2)}" if link else ""
