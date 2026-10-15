"""ghost_inject — when the turn threshold is reached, nudge the assistant
to compress the buffer via session_summarize. Ephemeral, cache-friendly.

NOTE: event.config is None on this hook — settings come from session_store.
Not privacy-aware: withheld in private chats by core.
"""
import os
import sys

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

_MAX_GHOST_CHARS = 1800  # stay under the 2KB envelope cap


def ghost_inject(event):
    try:
        import session_store as store

        chat = event.chat_name or "default"
        session = store.load_session(chat)
        pending = session.get("turns", [])
        threshold, _ = store.get_settings()

        if len(pending) < threshold:
            return  # no contribution this turn

        parts = []
        parts.append(
            f"Session buffer for this chat reached {len(pending)} turns "
            f"(threshold {threshold}). Call session_summarize NOW with an "
            f"aggressively compressed summary of the material below, then "
            f"continue your reply normally."
        )
        summary = session.get("summary")
        if summary:
            parts.append("PRIOR SUMMARY (fold into the new one): " + summary[:500])

        budget = _MAX_GHOST_CHARS - sum(len(p) for p in parts) - 100
        lines = []
        used = 0
        for t in pending:
            line = f"[{t.get('turn')}] U: {t.get('user', '')} | A: {t.get('ai', '')}"
            if used + len(line) > budget:
                lines.append(f"(+{len(pending) - len(lines)} more turns omitted)")
                break
            lines.append(line)
            used += len(line)
        parts.append("TURNS: " + " // ".join(lines))

        event.ghost_text = "\n".join(parts)[:_MAX_GHOST_CHARS]
    except Exception:
        pass  # never break the chat pipeline


handle = ghost_inject
