# Format recent chat turns for conversational RAG (generation only).

import os

DEFAULT_MAX_TURNS = 6


def max_history_turns() -> int:
    raw = os.getenv("CHAT_HISTORY_TURNS", str(DEFAULT_MAX_TURNS)).strip()
    try:
        turns = int(raw)
    except ValueError as exc:
        raise ValueError(f"CHAT_HISTORY_TURNS must be an integer, got {raw!r}.") from exc
    if turns <= 0:
        raise ValueError("CHAT_HISTORY_TURNS must be greater than 0.")
    return turns


def _is_system_message(message: dict) -> bool:
    if message.get("kind") == "system":
        return True
    content = message.get("content", "")
    if message.get("role") == "assistant" and content.startswith("Added ") and "document(s)" in content:
        return True
    return False


def select_chat_history(messages: list[dict], max_turns: int | None = None) -> list[dict]:
    """Return recent user/assistant chat turns, excluding system notices."""
    limit = max_turns if max_turns is not None else max_history_turns()
    chat: list[dict] = []
    for message in messages:
        role = message.get("role")
        if role not in ("user", "assistant"):
            continue
        if _is_system_message(message):
            continue
        chat.append(message)
    return chat[-(limit * 2) :]


def format_chat_history(messages: list[dict]) -> str:
    selected = select_chat_history(messages)
    if not selected:
        return ""
    lines: list[str] = []
    for message in selected:
        label = "User" if message["role"] == "user" else "Assistant"
        lines.append(f"{label}: {message.get('content', '').strip()}")
    return "\n\n".join(lines)
