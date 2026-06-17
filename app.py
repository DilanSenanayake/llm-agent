# Agentic Knowledge Workspace — Streamlit entrypoint.
#
# Run from the project root:
#     streamlit run app.py

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is importable when launched via Streamlit
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv
from langchain_core.documents import Document

from backend.agent import run_agent
from backend.chunker import chunk_text
from backend.document_loader import SUPPORTED_EXTENSIONS, load_document
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

_HIDE_SIDEBAR_CSS = """
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
        max-width: 100% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
</style>
"""


def _friendly_error(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


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
    st.session_state.pop("last_output", None)
    st.session_state.pop("last_format", None)
    return user_id


def _get_store(user_id: str):
    if "vector_store" not in st.session_state or st.session_state["vector_store"] is None:
        st.session_state["vector_store"] = load_vector_store(get_user_index_dir(user_id))
    return st.session_state["vector_store"]


# Save files, chunk, embed, merge into FAISS. Returns (chunk_count, error_or_none).
def process_uploaded_files(uploaded_files, user_id: str) -> tuple[int, str | None]:
    if not uploaded_files:
        return 0, "No files selected."

    all_docs: list[Document] = []
    for uf in uploaded_files:
        suffix = Path(uf.name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return 0, f"Unsupported type for {uf.name!r}. Only PDF and DOCX are allowed."

        uploads_dir = get_user_uploads_dir(user_id)
        dest = uploads_dir / uf.name
        try:
            dest.write_bytes(uf.getvalue())
        except Exception as exc:
            return 0, f"Could not save {uf.name}: {_friendly_error(exc)}"

        try:
            text = load_document(dest)
        except ValueError as exc:
            return 0, _friendly_error(exc)
        except Exception as exc:
            return 0, f"Failed to read {uf.name}: {_friendly_error(exc)}"

        chunks = chunk_text(text, chunk_size_words=500, overlap_words=50)
        if not chunks:
            return 0, f"No chunks produced from {uf.name} (empty after processing)."

        for i, chunk in enumerate(chunks):
            all_docs.append(
                Document(
                    page_content=chunk,
                    metadata={"source": uf.name, "chunk_index": i},
                )
            )

    index_dir = get_user_index_dir(user_id)
    try:
        existing = load_vector_store(index_dir)
        store = build_or_merge_store(all_docs, existing=existing)
        save_vector_store(store, index_dir)
    except Exception as exc:
        return 0, f"Indexing failed: {_friendly_error(exc)}"

    touch_session(user_id)
    st.session_state["vector_store"] = store
    return len(all_docs), None


def main() -> None:
    st.set_page_config(
        page_title="Agentic Knowledge Workspace",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    st.markdown(_HIDE_SIDEBAR_CSS, unsafe_allow_html=True)

    user_id = _ensure_user_id()

    st.title("Agentic Knowledge Workspace")
    st.caption(
        "Upload documents, index them locally, and ask focused questions "
        "with RAG + Gemini — answers grounded in the most relevant passages."
    )

    col_u, col_q = st.columns((1, 1), gap="large")

    with col_u:
        st.subheader("1. Document upload")
        uploaded = st.file_uploader(
            "PDF or DOCX",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            help="Files are stored locally for your session.",
        )

        if st.button("Process uploaded documents", type="primary"):
            with st.spinner("Extracting text, chunking, embedding, and updating FAISS…"):
                count, err = process_uploaded_files(uploaded, user_id)
            if err:
                st.error(err)
            else:
                st.success(f"Indexed {count} chunk(s) successfully.")

        st.subheader("Processing status")
        store = _get_store(user_id)
        if store is None:
            st.info("No vector index yet. Upload and process documents to begin.")
        else:
            try:
                n = store.index.ntotal  # type: ignore[attr-defined]
            except Exception:
                n = "unknown"
            st.success(f"Vector index ready ({n} vectors).")

    with col_q:
        st.subheader("2. Ask the workspace")
        instruction = st.text_area(
            "Your question or instruction (required)",
            height=140,
            placeholder=(
                'e.g. "What are the termination clauses?" · '
                '"Summarize the data retention policy" · '
                '"List all SLA thresholds" · '
                '"Compare Plan A vs Plan B on pricing"'
            ),
            help="This text is used to find relevant passages in your documents.",
        )

        format_options = {
            "Answer": "answer",
            "Brief summary": "brief_summary",
            "Extract": "extract",
            "Compare": "compare",
        }
        selected_label = st.selectbox(
            "Response format",
            options=list(format_options.keys()),
            index=0,
            help=(
                "Answer: direct response. Brief summary: short overview of your topic. "
                "Extract: lists, tables, or key facts. Compare: side-by-side (name both items)."
            ),
        )
        response_format = format_options[selected_label]

        do_generate = st.button("Generate", type="primary", use_container_width=True)

        st.subheader("3. Generated output")
        output_placeholder = st.container()

        if do_generate:
            store = _get_store(user_id)
            if store is None:
                st.warning("Process at least one document before generating output.")
            elif not (instruction or "").strip():
                st.warning("Enter a question or instruction before generating.")
            else:
                with st.spinner("Retrieving context and calling Gemini…"):
                    try:
                        text, fmt = run_agent(
                            store,
                            user_instruction=instruction,
                            response_format=response_format,
                        )
                    except ValueError as exc:
                        st.error(_friendly_error(exc))
                    except RuntimeError as exc:
                        st.error(_friendly_error(exc))
                    except Exception as exc:
                        st.error(f"Unexpected error: {_friendly_error(exc)}")
                    else:
                        touch_session(user_id)
                        st.session_state["last_output"] = text
                        st.session_state["last_format"] = fmt
                        with output_placeholder:
                            st.caption(f"Format: **{fmt}**")
                            st.markdown(text)
                        st.download_button(
                            label="Download as TXT",
                            data=text,
                            file_name=f"output_{fmt}.txt",
                            mime="text/plain",
                            use_container_width=False,
                        )

        elif st.session_state.get("last_output"):
            with output_placeholder:
                st.caption(f"Format: **{st.session_state.get('last_format', 'unknown')}**")
                st.markdown(st.session_state["last_output"])
            st.download_button(
                label="Download last output as TXT",
                data=st.session_state["last_output"],
                file_name=f"output_{st.session_state.get('last_format', 'result')}.txt",
                mime="text/plain",
            )


if __name__ == "__main__":
    main()
