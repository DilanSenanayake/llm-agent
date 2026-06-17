# Agentic Knowledge Workspace — Streamlit entrypoint.
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
from langchain_core.documents import Document

from backend.agent import run_agent
from backend.generator import ResponseFormat
from backend.chunker import chunk_text
from backend.document_loader import SUPPORTED_EXTENSIONS, load_document
from backend.storage import (
    check_upload_capacity,
    format_bytes,
    get_storage_usage,
)
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
from backend.vector_store import (
    build_or_merge_store,
    load_vector_store,
    save_vector_store,
)

load_dotenv()

_CHAT_CSS = """
<style>
    section[data-testid="stSidebar"],
    div[data-testid="stSidebar"],
    [data-testid="collapsedControl"],
    div[data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    div[data-testid="stAppViewContainer"] > section.main {
        width: 100% !important;
        max-width: 100% !important;
    }
    div[data-testid="stAppViewContainer"] > section.main > div.block-container {
        max-width: 52rem !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    [data-testid="stChatMessage"] {
        padding: 0.75rem 0 !important;
    }
    .storage-bar {
        font-size: 0.8rem;
        color: #6b7280;
        margin-bottom: 0.25rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatInput"]) {
        padding: 0.4rem 0.5rem 0.5rem !important;
        margin-top: 0.5rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatInput"]) [data-testid="column"]:first-child {
        min-width: 7.5rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatInput"]) [data-testid="stSelectbox"] label {
        display: none;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatInput"]) [data-testid="stSelectbox"] > div > div {
        min-height: 2.875rem;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:has([data-testid="stChatInput"]) [data-testid="stChatInput"] {
        margin-top: 0;
    }
</style>
"""

_WELCOME = (
    "Hi! Upload **PDF** or **DOCX** files in the area above, "
    "then ask questions about them. Pick a response type on the left of the chat bar "
    "or leave **Auto** to detect it from your message."
)

FORMAT_OPTIONS: dict[str, ResponseFormat | Literal["auto"]] = {
    "Auto": "auto",
    "Answer": "answer",
    "Brief summary": "brief_summary",
    "Extract": "extract",
    "Compare": "compare",
}

FORMAT_LABELS = {v: k for k, v in FORMAT_OPTIONS.items()}


def _friendly_error(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _init_messages() -> None:
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": _WELCOME},
        ]


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
    st.session_state["user_id"] = user_id
    st.session_state["vector_store"] = None
    st.session_state.pop("last_upload_key", None)
    st.session_state["messages"] = [{"role": "assistant", "content": _WELCOME}]
    return user_id


def _get_store(user_id: str):
    if "vector_store" not in st.session_state or st.session_state["vector_store"] is None:
        st.session_state["vector_store"] = load_vector_store(get_user_index_dir(user_id))
    return st.session_state["vector_store"]


def _upload_fingerprint(uploaded_files) -> tuple[tuple[str, int], ...]:
    return tuple((uf.name, len(uf.getvalue())) for uf in uploaded_files)


def process_uploaded_files(uploaded_files, user_id: str) -> tuple[list[str], int, str | None]:
    if not uploaded_files:
        return [], 0, None

    incoming = [(uf.name, len(uf.getvalue())) for uf in uploaded_files]
    ok, err = check_upload_capacity(user_id, incoming)
    if not ok:
        return [], 0, err

    all_docs: list[Document] = []
    saved_names: list[str] = []
    uploads_dir = get_user_uploads_dir(user_id)

    for uf in uploaded_files:
        suffix = Path(uf.name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return [], 0, f"Unsupported type for {uf.name!r}. Only PDF and DOCX are allowed."

        dest = uploads_dir / uf.name
        try:
            dest.write_bytes(uf.getvalue())
        except Exception as exc:
            return [], 0, f"Could not save {uf.name}: {_friendly_error(exc)}"

        try:
            text = load_document(dest)
        except ValueError as exc:
            return [], 0, _friendly_error(exc)
        except Exception as exc:
            return [], 0, f"Failed to read {uf.name}: {_friendly_error(exc)}"

        chunks = chunk_text(text, chunk_size_words=500, overlap_words=50)
        if not chunks:
            return [], 0, f"No chunks produced from {uf.name} (empty after processing)."

        for i, chunk in enumerate(chunks):
            all_docs.append(
                Document(
                    page_content=chunk,
                    metadata={"source": uf.name, "chunk_index": i},
                )
            )
        saved_names.append(uf.name)

    index_dir = get_user_index_dir(user_id)
    try:
        existing = load_vector_store(index_dir)
        store = build_or_merge_store(all_docs, existing=existing)
        save_vector_store(store, index_dir)
    except Exception as exc:
        return [], 0, f"Indexing failed: {_friendly_error(exc)}"

    touch_session(user_id)
    st.session_state["vector_store"] = store
    return saved_names, len(all_docs), None


def _render_storage_bar(user_id: str) -> None:
    used, limit = get_storage_usage(user_id)
    pct = min(100, int(100 * used / limit)) if limit else 0
    st.markdown(
        f'<div class="storage-bar">Storage: {format_bytes(used)} / {format_bytes(limit)} ({pct}%)</div>',
        unsafe_allow_html=True,
    )
    st.progress(pct / 100)


def main() -> None:
    st.set_page_config(
        page_title="Knowledge Chat",
        page_icon="💬",
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    st.markdown(_CHAT_CSS, unsafe_allow_html=True)

    user_id = _ensure_user_id()
    _init_messages()

    st.title("Knowledge Chat")

    with st.container(border=True):
        st.markdown("**📎 Attach documents**")
        st.caption("PDF or DOCX · indexed automatically on upload")
        _render_storage_bar(user_id)
        uploaded = st.file_uploader(
            "Choose files",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            label_visibility="collapsed",
        )

        if uploaded:
            fingerprint = _upload_fingerprint(uploaded)
            if fingerprint != st.session_state.get("last_upload_key"):
                with st.spinner("Indexing documents…"):
                    names, chunk_count, err = process_uploaded_files(uploaded, user_id)
                if err:
                    st.session_state["messages"].append(
                        {"role": "assistant", "content": f"⚠️ {err}"}
                    )
                else:
                    file_list = ", ".join(f"**{n}**" for n in names)
                    st.session_state["messages"].append(
                        {
                            "role": "assistant",
                            "content": (
                                f"Added {len(names)} document(s): {file_list}. "
                                f"Indexed {chunk_count} passage(s). Ask me anything about them."
                            ),
                        }
                    )
                st.session_state["last_upload_key"] = fingerprint
                st.rerun()

    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            if message.get("format"):
                st.caption(f"Format: **{FORMAT_LABELS.get(message['format'], message['format'])}**")
            st.markdown(message["content"])

    with st.container(border=True):
        type_col, chat_col = st.columns(
            [1.35, 4.65],
            vertical_alignment="bottom",
            gap="small",
        )
        with type_col:
            selected_label = st.selectbox(
                "Response type",
                options=list(FORMAT_OPTIONS.keys()),
                index=0,
                label_visibility="collapsed",
                help=(
                    "Auto picks the format from your message (e.g. compare, summarize, extract). "
                    "Or choose Answer, Brief summary, Extract, or Compare explicitly."
                ),
            )
        with chat_col:
            prompt = st.chat_input("Ask about your documents…")

    response_format = FORMAT_OPTIONS[selected_label]

    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            store = _get_store(user_id)
            fmt = None
            if store is None:
                reply = (
                    "Upload at least one PDF or DOCX in the attach area above, "
                    "then ask your question."
                )
                st.markdown(reply)
            else:
                with st.spinner("Thinking…"):
                    try:
                        reply, fmt = run_agent(
                            store,
                            user_instruction=prompt,
                            response_format=response_format,
                        )
                        touch_session(user_id)
                    except (ValueError, RuntimeError) as exc:
                        reply = f"⚠️ {_friendly_error(exc)}"
                        fmt = None
                    except Exception as exc:
                        reply = f"⚠️ Unexpected error: {_friendly_error(exc)}"
                        fmt = None
                    else:
                        st.caption(f"Format: **{FORMAT_LABELS.get(fmt, fmt)}**")
                st.markdown(reply)

        assistant_msg: dict = {"role": "assistant", "content": reply}
        if fmt:
            assistant_msg["format"] = fmt
        st.session_state["messages"].append(assistant_msg)


if __name__ == "__main__":
    main()
