# Single-chat session state helpers.


def init_chats() -> None:
    import streamlit as st

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []


def reset_chats() -> None:
    import streamlit as st

    st.session_state.chat_messages = []


def active_messages() -> list[dict]:
    import streamlit as st

    return st.session_state.get("chat_messages", [])


def append_message(message: dict) -> None:
    import streamlit as st

    st.session_state.chat_messages.append(message)


def has_user_messages() -> bool:
    return any(
        m.get("kind") == "chat" and m.get("role") == "user"
        for m in active_messages()
    )
