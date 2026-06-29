# DocuChat — Streamlit entrypoint.
#
# Run from the project root:
#     streamlit run app.py

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

from backend.agent import stream_agent
from backend.chats import (
    active_messages,
    append_message,
    has_user_messages,
    init_chats,
    reset_chats,
)
from backend.documents import (
    indexed_file_names,
    list_uploaded_documents,
    process_uploaded_files,
    remove_uploaded_documents,
)
from backend.generator import ResponseFormat
from backend.storage import format_bytes, get_storage_usage
from backend.users import (
    cleanup_expired_sessions,
    create_session,
    delete_user_workspace,
    ensure_user_dirs,
    generate_user_id,
    get_user_index_dir,
    get_user_uploads_dir,
    is_session_valid,
    touch_session,
)
from backend.vector_store import clear_vector_store, load_vector_store
from frontend.layout import inject_layout
from frontend.theme import inject_theme

load_dotenv()

FORMAT_OPTIONS: dict[str, ResponseFormat | Literal["auto"]] = {
    "Auto": "auto",
    "Answer": "answer",
    "Brief summary": "brief_summary",
    "Extract": "extract",
    "Compare": "compare",
}

FORMAT_LABELS = {v: k for k, v in FORMAT_OPTIONS.items()}

FORMAT_DESCRIPTIONS: dict[str, str] = {
    "Auto": "Picks a format from keywords in your message.",
    "Answer": "Direct answer to a specific question.",
    "Brief summary": "Short overview of the topic you name.",
    "Extract": "Bullets, tables, or key facts only.",
    "Compare": "Side-by-side — name both items in your message.",
}

SUGGESTED_PROMPTS: list[dict[str, str | ResponseFormat]] = [
    {"format": "answer", "prompt": "Main risks?"},
    {"format": "brief_summary", "prompt": "Key themes"},
    {"format": "extract", "prompt": "Deadlines & requirements"},
    {"format": "compare", "prompt": "Methodology vs findings"},
]


def _friendly_error(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _loading_html(label: str = "Searching your documents") -> str:
    return (
        f'<div class="dc-loader">'
        f'<span class="dc-loader-dots"><span></span><span></span><span></span></span>'
        f"<span>{label}</span>"
        f"</div>"
    )


def _ensure_user_id() -> str:
    cleanup_expired_sessions()

    user_id = st.session_state.get("user_id")
    if user_id and is_session_valid(user_id):
        touch_session(user_id)
        return user_id

    if user_id:
        delete_user_workspace(user_id)

    user_id = generate_user_id()
    ensure_user_dirs(user_id)
    create_session(user_id)
    st.session_state.user_id = user_id
    st.session_state.vector_store = None
    st.session_state.pop("last_upload_key", None)
    st.session_state.pop("uploader_file_names", None)
    st.session_state.pop("uploader_had_files", None)
    reset_chats()
    return user_id


def _get_store(user_id: str):
    if "vector_store" not in st.session_state or st.session_state.vector_store is None:
        st.session_state.vector_store = load_vector_store(get_user_index_dir(user_id))
    return st.session_state.vector_store


def _invalidate_store(user_id: str) -> None:
    st.session_state.vector_store = load_vector_store(get_user_index_dir(user_id))


def _upload_fingerprint(uploaded_files) -> tuple[tuple[str, int], ...]:
    return tuple((uf.name, len(uf.getvalue())) for uf in uploaded_files)


def _reset_sidebar_uploader() -> None:
    st.session_state.sidebar_uploader_key = (
        st.session_state.get("sidebar_uploader_key", 0) + 1
    )
    st.session_state.pop("last_upload_key", None)


def _init_uploader_tracking(user_id: str) -> None:
    if "uploader_file_names" not in st.session_state:
        st.session_state.uploader_file_names = indexed_file_names(user_id)


def _widget_file_names(uploaded) -> set[str] | None:
    """Names in the uploader widget, or None if the widget was not touched."""
    if uploaded is not None:
        st.session_state.uploader_had_files = True
        return {uf.name for uf in uploaded}
    if st.session_state.get("uploader_had_files"):
        return set()
    return None


def _sync_uploader_with_disk(user_id: str, uploaded) -> bool:
    """Sync disk index with the uploader widget (adds and removals)."""
    _init_uploader_tracking(user_id)
    widget_names = _widget_file_names(uploaded)
    if widget_names is None:
        return False

    changed = False
    tracked: set[str] = set(st.session_state.uploader_file_names)
    removed = tracked - widget_names
    if removed:
        err = remove_uploaded_documents(user_id, removed)
        if err:
            st.error(err)
            return False
        tracked -= removed
        changed = True

    if uploaded:
        fingerprint = _upload_fingerprint(uploaded)
        if fingerprint != st.session_state.get("last_upload_key"):
            with st.status("Indexing…", expanded=False) as status:
                names, chunk_count, err = process_uploaded_files(uploaded, user_id)
                if err:
                    status.update(label="Failed", state="error")
                    st.error(err)
                    return False
                status.update(label=f"{len(names)} file(s) indexed", state="complete")
                append_message(
                    {
                        "role": "assistant",
                        "kind": "system",
                        "content": (
                            f"Indexed **{', '.join(names)}** "
                            f"({chunk_count} passages)."
                        ),
                    }
                )
            st.session_state.last_upload_key = fingerprint
            tracked = indexed_file_names(user_id)
            changed = True

    st.session_state.uploader_file_names = tracked
    if not tracked:
        st.session_state.uploader_had_files = False
    return changed


def _clear_workspace(user_id: str) -> None:
    clear_vector_store(get_user_index_dir(user_id))
    uploads_dir = get_user_uploads_dir(user_id)
    if uploads_dir.exists():
        for path in uploads_dir.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                path.unlink()
    st.session_state.vector_store = None
    st.session_state.pop("last_upload_key", None)
    st.session_state.uploader_file_names = set()
    st.session_state.uploader_had_files = False
    reset_chats()
    _reset_sidebar_uploader()


def _render_sidebar(user_id: str) -> None:
    st.markdown(
        '<p class="dc-logo">Docu<span>Chat</span></p>',
        unsafe_allow_html=True,
    )

    st.markdown('<p class="dc-sidebar-label">Documents</p>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload PDF or DOCX",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key=f"sidebar_uploader_{st.session_state.get('sidebar_uploader_key', 0)}",
    )

    if _sync_uploader_with_disk(user_id, uploaded):
        _invalidate_store(user_id)
        st.rerun()

    docs = list_uploaded_documents(user_id)
    used, limit = get_storage_usage(user_id)
    if docs:
        st.caption(f"{len(docs)} file(s) · {format_bytes(used)} / {format_bytes(limit)}")
    else:
        st.caption(f"{format_bytes(used)} / {format_bytes(limit)}")

    with st.expander("Settings", expanded=False):
        st.selectbox(
            "Default format",
            options=list(FORMAT_OPTIONS.keys()),
            key="settings_format",
        )
        st.caption(
            FORMAT_DESCRIPTIONS.get(
                st.session_state.get("settings_format", "Auto"),
                "",
            )
        )
        if st.button("Clear workspace", use_container_width=True):
            _clear_workspace(user_id)
            st.rerun()


def _render_home() -> None:
    st.markdown(
        """
        <div class="dc-home-card">
            <div class="dc-home-icon">💬</div>
            <div class="dc-home-title">Ask about your documents</div>
            <div class="dc-home-sub">
                Upload in the sidebar, choose a format, ask a focused question.
            </div>
            <p class="dc-prompts-label">Examples</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    for i, item in enumerate(SUGGESTED_PROMPTS):
        fmt_label = FORMAT_LABELS[item["format"]]
        prompt = str(item["prompt"])
        with cols[i]:
            st.markdown(
                f'<div class="dc-chip-btn"><span class="dc-chip-format">{fmt_label}</span>',
                unsafe_allow_html=True,
            )
            if st.button(prompt, key=f"prompt_{i}", use_container_width=True):
                st.session_state.pending_prompt = prompt
                st.session_state.pending_format = item["format"]
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)


def _render_messages() -> None:
    for message in active_messages():
        role = message.get("role", "assistant")
        if message.get("kind") == "system" and not message.get("content", "").startswith(
            "Indexed"
        ):
            continue
        with st.chat_message(role):
            if message.get("format"):
                st.caption(f"**{FORMAT_LABELS.get(message['format'], message['format'])}**")
            st.markdown(message.get("content", ""))


def _stream_assistant_reply(
    user_id: str,
    prompt: str,
    response_format: ResponseFormat | Literal["auto"],
    prior: list[dict],
) -> None:
    store = _get_store(user_id)
    if store is None:
        reply = "Upload at least one PDF or DOCX to get started."
        with st.chat_message("assistant"):
            st.markdown(reply)
        append_message({"role": "assistant", "content": reply, "kind": "chat"})
        return

    fmt: ResponseFormat | None = None
    with st.chat_message("assistant"):
        slot = st.empty()
        slot.markdown(_loading_html("Searching your documents"), unsafe_allow_html=True)
        try:
            stream, fmt, _docs = stream_agent(
                store,
                user_instruction=prompt,
                response_format=response_format,
                chat_messages=prior,
            )
            slot.markdown(_loading_html("Thinking..."), unsafe_allow_html=True)
            parts: list[str] = []
            for chunk in stream:
                parts.append(chunk)
                slot.markdown("".join(parts))
            reply = "".join(parts).strip()
            if not reply:
                reply = "No response was generated. Try again."
            slot.markdown(reply)
            if fmt and reply and not reply.startswith("⚠️"):
                st.caption(f"**{FORMAT_LABELS.get(fmt, fmt)}**")
            touch_session(user_id)
        except (ValueError, RuntimeError) as exc:
            reply = f"⚠️ {_friendly_error(exc)}"
            fmt = None
            slot.markdown(reply)
        except Exception as exc:
            reply = f"⚠️ Unexpected error: {_friendly_error(exc)}"
            fmt = None
            slot.markdown(reply)

    msg: dict = {"role": "assistant", "content": reply, "kind": "chat"}
    if fmt:
        msg["format"] = fmt
    append_message(msg)


def _queue_prompt(prompt: str, response_format: ResponseFormat | Literal["auto"]) -> None:
    st.session_state.pending_generation = {
        "prompt": prompt.strip(),
        "format": response_format,
    }
    st.rerun()


def _render_input_bar() -> None:
    default_format = st.session_state.get("settings_format", "Auto")
    format_idx = list(FORMAT_OPTIONS.keys()).index(default_format)

    with st.form("chat_form", clear_on_submit=True):
        c_fmt, c_msg, c_send = st.columns([1.1, 5, 0.55], vertical_alignment="bottom")
        with c_fmt:
            selected = st.selectbox(
                "Format",
                options=list(FORMAT_OPTIONS.keys()),
                index=format_idx,
                label_visibility="collapsed",
                key="chat_format_select",
            )
        with c_msg:
            prompt = st.text_input(
                "Message",
                placeholder="Ask a focused question…",
                label_visibility="collapsed",
                key="chat_input",
            )
        with c_send:
            submitted = st.form_submit_button("↑", use_container_width=True)

    if submitted:
        if (prompt or "").strip():
            st.session_state.pending_generation = {
                "prompt": prompt.strip(),
                "format": FORMAT_OPTIONS[selected],
            }
            st.rerun()
        st.session_state.chat_empty_warning = True
        st.rerun()


def main() -> None:
    st.set_page_config(
        page_title="DocuChat",
        page_icon="💬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    inject_layout()

    user_id = _ensure_user_id()
    init_chats()

    with st.sidebar:
        _render_sidebar(user_id)

    default_fmt: ResponseFormat | Literal["auto"] = FORMAT_OPTIONS.get(
        st.session_state.get("settings_format", "Auto"),
        "auto",
    )

    # Example-chip click
    pending_prompt = st.session_state.pop("pending_prompt", None)
    pending_format = st.session_state.pop("pending_format", None)
    if pending_prompt:
        _queue_prompt(
            pending_prompt,
            pending_format if pending_format else default_fmt,
        )

    # Queued generation (form submit or example)
    gen = st.session_state.pop("pending_generation", None)

    if gen:
        prior = list(active_messages())
        append_message({"role": "user", "content": gen["prompt"], "kind": "chat"})

    if has_user_messages():
        _render_messages()
        if gen:
            _stream_assistant_reply(user_id, gen["prompt"], gen["format"], prior)
    else:
        _render_home()

    if st.session_state.pop("chat_empty_warning", False):
        st.warning("Enter a question or instruction.")
    _render_input_bar()


if __name__ == "__main__":
    main()
