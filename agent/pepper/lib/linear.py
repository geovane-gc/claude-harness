"""Which Linear tools a run gets. Runs that answer someone or build a change read cards; only the owner's own
orders in the control channel create or change them. The guard (pepper/guard/linear_guard.py) enforces the same lists."""

PREFIX = "mcp__claude_ai_Linear__"
READ = ("get_issue", "list_issues", "list_comments", "get_project", "list_projects", "list_issue_statuses",
        "list_issue_labels", "list_cycles", "list_teams", "get_team", "list_users", "get_user", "get_document",
        "list_documents", "list_milestones", "get_milestone")
WRITE = ("save_issue", "save_comment")
READ_KINDS = ("bot", "person", "build", "prfix")
WRITE_KINDS = ("order", "answer")


def enabled():
    from .settings import CONFIG
    return bool(CONFIG.get("linear"))


def tools(kind):
    if not enabled():
        return []
    names = READ + WRITE if kind in WRITE_KINDS else READ if kind in READ_KINDS else ()
    return [PREFIX + name for name in names]
