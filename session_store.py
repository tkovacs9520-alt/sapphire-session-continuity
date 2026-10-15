"""Shared session buffer storage for session_continuity.

Chat-scoped JSON files under sessions/ inside the plugin dir.
Never touches the core memory system.
"""
import json
import os
from datetime import datetime

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_DIR = os.path.join(PLUGIN_DIR, "sessions")

DEFAULT_THRESHOLD = 10
DEFAULT_MAX_TURN_CHARS = 400


def get_settings():
    """Read plugin settings with safe fallbacks (some hooks have no config)."""
    threshold = DEFAULT_THRESHOLD
    max_chars = DEFAULT_MAX_TURN_CHARS
    try:
        from core.plugin_loader import plugin_loader
        getter = getattr(plugin_loader, "get_plugin_settings", None)
        if getter:
            s = getter("session_continuity") or {}
            threshold = int(s.get("PIPELINE_SUMMARIZE_THRESHOLD", threshold))
            max_chars = int(s.get("PIPELINE_MAX_TURN_CHARS", max_chars))
    except Exception:
        pass
    return max(2, threshold), max(50, max_chars)


def _ensure_dirs():
    os.makedirs(SESSION_DIR, exist_ok=True)


def safe_id(chat_name):
    s = "".join(c if c.isalnum() or c in "-_" else "_" for c in (chat_name or "default"))
    return s[:80] or "default"


def session_path(chat_name):
    return os.path.join(SESSION_DIR, f"{safe_id(chat_name)}.json")


def _blank(chat_name):
    return {
        "chat": chat_name or "default",
        "created": datetime.now().isoformat(),
        "turns": [],
        "turn_count": 0,
        "total_turns_ever": 0,
        "summary": None,
        "last_summarized_at": None,
        "last_committed_at": None,
    }


def load_session(chat_name):
    path = session_path(chat_name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "turns" in data:
                return data
        except Exception:
            pass  # corrupt = start fresh
    return _blank(chat_name)


def save_session(chat_name, data):
    _ensure_dirs()
    data["last_updated"] = datetime.now().isoformat()
    tmp = session_path(chat_name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, session_path(chat_name))


def delete_session(chat_name):
    try:
        path = session_path(chat_name)
        if os.path.exists(path):
            os.remove(path)
            return True
    except Exception:
        pass
    return False


def list_sessions():
    _ensure_dirs()
    out = []
    for fname in os.listdir(SESSION_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SESSION_DIR, fname), "r", encoding="utf-8") as f:
                d = json.load(f)
            out.append({
                "chat": d.get("chat", fname[:-5]),
                "pending": len(d.get("turns", [])),
                "has_summary": bool(d.get("summary")),
                "updated": d.get("last_updated", ""),
            })
        except Exception:
            continue
    out.sort(key=lambda s: s.get("updated") or "", reverse=True)
    return out


def most_recent_chat():
    sessions = list_sessions()
    return sessions[0]["chat"] if sessions else None
