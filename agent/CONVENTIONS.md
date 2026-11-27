# Where new things go in your agent folder
| Kind | Lives in | Loaded by | Never |
|---|---|---|---|
| Agent task prompt (system prompt of a `claude -p` run) | `pepper/skills/<task>/SKILL.md` | only the agent's lean runs (`--system-prompt-file`, `--setting-sources ""`); they do not load the plugin | name it like a plugin skill |
| Agent code | `pepper/` (`watch.py`, `lib/`, `guard/` with its tests) | launchd, from `pepper/launchd/watch.plist` (written by `install.sh`) | |
| Agent config | `pepper/config.json` (copied from `config.example.json`) | `watch.py` and the guards | put a secret in it |
| Shared CLI helper | `bin/<name>` (no secrets inside; secrets via `bin/secret`, in the macOS Keychain) | the agent and your sessions | |
| Knowledge | `knowledge/` (policies ship here; add an `INDEX.md` as it grows) | read on demand | copy repo docs instead of pointing to them |
| Skills, commands, hooks for your interactive sessions | the plugin (`/plugin install`) or a plugin of your own | every session | edit the plugin cache: it is replaced on update |
| Scheduled tasks | the Claude app's own task file; its prompt only points to a skill | Claude app | put logic in the task prompt |
After changing `pepper/guard/`, run `python3 -m unittest pepper/guard/test_guards.py` from this folder.
