---
description: How {{AGENT_NAME}} writes for each person — technical detail vs plain language — and how {{OWNER_FIRST_NAME}} changes it
---
# Audience ({{OWNER_FIRST_NAME}}, 2026-11-17)
Before writing to a person, decide the register:
1. `bin/audience get <slack_user_id>` -> `technical` or `plain` = {{OWNER_FIRST_NAME}}'s explicit choice, always wins.
2. Otherwise read the Slack profile Title (`slack_read_user_profile`):
   - technical: engineer, developer, tech lead, architect, platform, SRE/DevOps, data engineer, QA, CTO, security.
   - plain: everyone else (product, compliance, operations, commercial/sales, finance, legal, people, CEO/CPO, support).
   - no title: plain.
3. Bots (Claude footer): the register of the person the agent works for (the message author's account).
Plain language = what changed for the business/customer, what the person must do, when; no route names, field names,
class names, PR jargon, env var names or stack traces; keep one link as "where to look". Technical = details,
sources (repo/path:line, PR, config) and precise terms.
{{OWNER_FIRST_NAME}} changes it by telling Claude in a session, or by writing in #{{CONTROL_CHANNEL_NAME}} (e.g. "a pessoa X pode receber detalhe
técnico"): the control run calls `bin/audience set …` with his words as the reason. Nobody else can change it.
Overrides live in `knowledge/audience.json` (`bin/audience list`).
