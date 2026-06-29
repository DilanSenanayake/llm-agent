# Chat history — session state with per-user disk persistence.

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


def init_chats(user_id: str) -> None:
    import streamlit as st

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = load_chats(user_id)


def reset_chats(user_id: str) -> None:
    import streamlit as st

    st.session_state.chat_messages = []
    save_chats(user_id, [])


def set_messages(user_id: str, messages: list[dict]) -> None:
    import streamlit as st

    st.session_state.chat_messages = messages
    save_chats(user_id, messages)


def active_messages() -> list[dict]:
    import streamlit as st

    return st.session_state.get("chat_messages", [])


def append_message(user_id: str, message: dict) -> None:
    import streamlit as st

    st.session_state.chat_messages.append(message)
    save_chats(user_id, st.session_state.chat_messages)


def has_user_messages() -> bool:
    return any(
        m.get("kind") == "chat" and m.get("role") == "user"
        for m in active_messages()
    )
