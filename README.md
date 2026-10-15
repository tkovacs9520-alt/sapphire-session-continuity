# Session Continuity

A Sapphire plugin that keeps long chats sharp and recoverable — without bloating context.

## Why this exists

API prompt caching already solves most of the *cost* problem: re-sending a long
history is cheap on a cache hit. What caching does **not** do is shrink the
context. History still grows forever, attention still degrades, and every cache
expiry re-warms a bloated prompt at full price.

This plugin attacks the other half: it keeps the working context *small* by
capturing each exchange automatically and compressing the buffer into a rolling
summary. On local models — which have no caching and small context windows —
that difference is the whole ballgame.

It replaces an earlier tool-only design that depended on the assistant
remembering to log every turn. Models drift; turns went missing; the summary
cycle never fired. Capture is now automatic via hooks.

## How it works

1. **`post_chat` hook** — silently appends each exchange (truncated user message
   + assistant reply) to a per-chat JSON buffer. No LLM involvement, no cost.
2. **`ghost_inject` hook** — once pending turns hit the threshold, injects a
   compact, ephemeral nudge asking the assistant to compress the buffer. Ghost
   text is never saved to history and does not break the prompt cache.
3. **`chat_cleared` hook** — wipes that chat's buffer so a cleared chat starts clean.

## Tools

| Tool | Purpose |
|---|---|
| `session_summarize(summary, chat?)` | Store a compressed summary; clears the pending buffer. |
| `session_status(chat?)` | No args = list all buffers. With `chat` = full detail incl. the complete summary. **This is the manual retrieval path.** |
| `session_commit(chat?, tag?)` | Format summary + pending turns for `save_knowledge(category='session_memory', ...)`, then clear the session. |

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `PIPELINE_SUMMARIZE_THRESHOLD` | `10` | Pending turns before the ghost nudge fires. |
| `PIPELINE_MAX_TURN_CHARS` | `400` | Max characters captured per turn, split across user/assistant. |

## Design decisions

- **Chat-scoped only.** Buffers are keyed by chat name. Nothing bleeds between
  chats, and the plugin never touches Sapphire's core memory system.
- **No auto-injection.** Summaries are *not* pushed into context on a new or
  cleared chat — that would reintroduce exactly the bloat this plugin exists to
  prevent. Retrieval is manual, via `session_status`.
- **Deliberately not `privacy_aware`.** Because this plugin mirrors conversation
  text to disk, core withholds every hook in private chats. Nothing is captured,
  nothing is written. That is the intended behavior, not a limitation.
- **The only bridge to long-term memory is manual.** `session_commit` is the
  single path from a session buffer into the knowledge base.
- **Fails silently, never fatally.** Every hook swallows its own exceptions;
  corrupt buffer files are discarded and rebuilt. A bug here must never break
  the chat pipeline.

## Install

Drop the folder into `user/plugins/session_continuity/`, rescan plugins, and
enable it. The tools must also be added to your active toolset
(Persona → Toolsets). Note that `user/toolsets/toolsets.json` keys its tool
lists under `functions`, not `tools`.

## Uninstall / disable

Toggle the plugin off. Capture stops immediately; the core memory system is
entirely unaffected.

## Layout

```
plugin.json
session_store.py              shared buffer storage
hooks/post_chat.py            automatic turn capture
hooks/ghost_inject.py         threshold nudge (ephemeral, cache-friendly)
hooks/chat_cleared.py         buffer cleanup
tools/session_continuity_tools.py
```
