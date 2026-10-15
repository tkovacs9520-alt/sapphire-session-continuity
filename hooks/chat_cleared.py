"""chat_cleared — a cleared chat starts with a clean session buffer."""
import os
import sys

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)


def chat_cleared(event):
    try:
        import session_store as store
        chat = (event.metadata or {}).get("chat")
        if chat:
            store.delete_session(chat)
    except Exception:
        pass


handle = chat_cleared
