# Chat history — per-user disk persistence (framework-agnostic).

from __future__ import annotations

import json
from pathlib import Path

from backend.users import get_user_root


def _chat_path(user_id: str) -> Path:
    return get_user_root(user_id) / "chat.json"


def load_chats(user_id: str) -> list[dict]:
    path = _chat_path(user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_chats(user_id: str, messages: list[dict]) -> None:
    path = _chat_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(messages), encoding="utf-8")


def get_messages(user_id: str) -> list[dict]:
    return load_chats(user_id)


def reset_chats(user_id: str) -> None:
    save_chats(user_id, [])


def set_messages(user_id: str, messages: list[dict]) -> None:
    save_chats(user_id, messages)


def append_message(user_id: str, message: dict) -> None:
    messages = load_chats(user_id)
    messages.append(message)
    save_chats(user_id, messages)


def has_user_messages(user_id: str) -> bool:
    return any(
        m.get("kind") == "chat" and m.get("role") == "user"
        for m in get_messages(user_id)
    )
