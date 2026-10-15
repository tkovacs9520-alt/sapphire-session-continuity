"""Tools for session_continuity: summarize, status (manual retrieval), commit."""
import os
import sys
from datetime import datetime

_PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PLUGIN_DIR not in sys.path:
    sys.path.insert(0, _PLUGIN_DIR)

ENABLED = True
EMOJI = '🧵'

AVAILABLE_FUNCTIONS = ['session_summarize', 'session_status', 'session_commit']

SETTINGS = {
    'PIPELINE_SUMMARIZE_THRESHOLD': 10,
    'PIPELINE_MAX_TURN_CHARS': 400,
}
SETTINGS_HELP = {
    'PIPELINE_SUMMARIZE_THRESHOLD': 'Pending turns before the ghost nudge asks for a summary (default 10)',
    'PIPELINE_MAX_TURN_CHARS': 'Max characters captured per turn, split across user/AI (default 400)',
}

TOOLS = [
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "session_summarize",
            "description": "Store an aggressively compressed summary of the session buffer. Replaces the previous summary and clears the pending turn buffer. Call when the ghost nudge signals the threshold, or manually anytime.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Compressed summary: key entities, decisions, action items, open threads. Drop filler."},
                    "chat": {"type": "string", "description": "Chat name. Defaults to the most recently active session."}
                },
                "required": ["summary"]
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "session_status",
            "description": "Manual retrieval path. No args = list all session buffers. With chat = full detail including the complete stored summary and recent turns. Use after a chat clear to restore working context on demand.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chat": {"type": "string", "description": "Chat name for detail view. Omit to list all sessions."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "is_local": True,
        "function": {
            "name": "session_commit",
            "description": "Push the session summary + pending turns to long-term knowledge. Call when user types /commit. Returns formatted content — you MUST then call save_knowledge(category='session_memory', content=<returned content>). Clears the session after.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chat": {"type": "string", "description": "Chat name. Defaults to the most recently active session."},
                    "tag": {"type": "string", "description": "Topic tag for retrieval (e.g. 'bankruptcy-filing', 'dream-team-pivot')"}
                },
                "required": []
            }
        }
    }
]


def _resolve_chat(arguments):
    import session_store as store
    chat = (arguments.get('chat') or '').strip()
    if chat:
        return chat
    return store.most_recent_chat() or 'default'


def execute(function_name, arguments, config, plugin_settings=None):
    import session_store as store

    if function_name == 'session_summarize':
        summary = (arguments.get('summary') or '').strip()
        if not summary:
            return "Error: summary cannot be empty.", False
        chat = _resolve_chat(arguments)
        session = store.load_session(chat)
        cleared = len(session.get('turns', []))
        session['summary'] = summary
        session['last_summarized_at'] = datetime.now().isoformat()
        session['turns'] = []
        session['turn_count'] = 0
        store.save_session(chat, session)
        return (
            f"Summary saved [{chat}]. {cleared} turns cleared. "
            f"Summary: {len(summary)} chars. Total turns ever: {session.get('total_turns_ever', 0)}. "
            f"Type /commit to push to long-term knowledge.",
            True
        )

    elif function_name == 'session_status':
        chat = (arguments.get('chat') or '').strip()
        if not chat:
            sessions = store.list_sessions()
            if not sessions:
                return "No session buffers found.", True
            lines = ["Session buffers (most recent first):"]
            for s in sessions:
                flag = " [has summary]" if s['has_summary'] else ""
                lines.append(f"  • {s['chat']} — {s['pending']} pending turns{flag} (updated {s['updated'][:16]})")
            return "\n".join(lines), True

        session = store.load_session(chat)
        lines = [
            f"Session: {session.get('chat')}",
            f"Pending turns: {len(session.get('turns', []))}",
            f"Total turns ever: {session.get('total_turns_ever', 0)}",
            f"Last summarized: {session.get('last_summarized_at') or 'never'}",
            f"Last committed: {session.get('last_committed_at') or 'never'}",
        ]
        if session.get('summary'):
            lines.append(f"\nFULL SUMMARY:\n{session['summary']}")
        else:
            lines.append("\nNo summary stored yet.")
        turns = session.get('turns', [])
        if turns:
            lines.append(f"\nRecent turns ({min(5, len(turns))} of {len(turns)}):")
            for t in turns[-5:]:
                lines.append(f"  [{t.get('turn')}] ({t.get('ts')}) U: {t.get('user')} | A: {t.get('ai')}")
        return "\n".join(lines), True

    elif function_name == 'session_commit':
        chat = _resolve_chat(arguments)
        tag = (arguments.get('tag') or '').strip()
        session = store.load_session(chat)
        summary = session.get('summary')
        pending = session.get('turns', [])
        if not summary and not pending:
            return f"Nothing to commit for [{chat}] — no summary and no pending turns.", False

        parts = [
            f"# Session: {chat}",
            f"Committed: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total turns: {session.get('total_turns_ever', 0)}",
        ]
        if tag:
            parts.append(f"Tag: {tag}")
        parts.append("")
        if summary:
            parts.append(f"## Summary\n{summary}")
        if pending:
            parts.append(f"\n## Pending turns ({len(pending)})")
            for t in pending:
                parts.append(f"[{t.get('turn')}] ({t.get('ts')}) U: {t.get('user')} | A: {t.get('ai')}")
        commit_content = "\n".join(parts)

        session['last_committed_at'] = datetime.now().isoformat()
        session['summary'] = None
        session['turns'] = []
        session['turn_count'] = 0
        session['total_turns_ever'] = 0
        store.save_session(chat, session)

        return (
            f"SESSION READY FOR COMMIT [{chat}].\n"
            f"Call save_knowledge(category='session_memory', content=<below>) now:\n\n"
            f"---COMMIT---\n{commit_content}\n---END COMMIT---",
            True
        )

    return f"Unknown function: {function_name}", False
