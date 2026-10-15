"""post_chat — auto-capture each exchange into the chat's session buffer.

Observational, no LLM involvement, errors never break the pipeline.
Not privacy-aware: this hook is withheld in private chats by core.
"""
import os
import sys
from datetime import datetime

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)


def post_chat(event):
    try:
        import session_store as store

        chat = event.chat_name or "default"
        user_text = (event.input or "").strip()
        ai_text = (event.response or "").strip()
        if not user_text and not ai_text:
            return

        _, max_chars = store.get_settings()
        half = max(25, max_chars // 2)

        def trunc(t, n):
            return t if len(t) <= n else t[:n] + "…"

        session = store.load_session(chat)
        session["turns"].append({
            "turn": session.get("turn_count", 0) + 1,
            "ts": datetime.now().strftime("%m-%d %H:%M"),
            "user": trunc(user_text, half),
            "ai": trunc(ai_text, half),
        })
        session["turn_count"] = session.get("turn_count", 0) + 1
        session["total_turns_ever"] = session.get("total_turns_ever", 0) + 1
        store.save_session(chat, session)
    except Exception:
        pass  # never break the chat pipeline


handle = post_chat
