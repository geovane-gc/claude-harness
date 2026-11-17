---
name: principle-what-not-how
description: "Apply when handing work to an agent that holds the knowledge of how it is done, such as an engineer that reads the repo's rules: a brief, a fix request, a doubt about its diff. Say what is wanted, why and what proves it; the agent decides how."
disable-model-invocation: true
---

# What, Not How

The agent that does the work holds the knowledge of how it is done. Tell it what is wanted, why and what proves it, and it decides how. A how you add is a guess made without that knowledge, and the agent follows it over what it knows.

- Pass on a how only when the user decided it or a playbook step hands it over, such as the sketch. Name a how the user decided as the user's.
- A how is any choice about the code that delivers what is wanted, such as where it goes, what it uses or is tested with, or an approach to avoid. For a retry, say "the publish is tried again before the failure reaches its caller".
- Raise a doubt about how the agent built something as a question.
