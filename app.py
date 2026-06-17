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
from backend.paths import DEFAULT_INDEX_DIR, UPLOADS_DIR
from backend.vector_store import (
    build_or_merge_store,
    clear_vector_store,
    load_vector_store,
    save_vector_store,
)

load_dotenv()

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _friendly_error(exc: BaseException) -> str:
    return str(exc).strip() or exc.__class__.__name__


def _get_store():
    if "vector_store" not in st.session_state or st.session_state["vector_store"] is None:
        st.session_state["vector_store"] = load_vector_store()
    return st.session_state["vector_store"]


def _invalidate_store_cache():
    st.session_state["vector_store"] = None


# Delete vector index, uploaded files, and in-memory session output.
def clear_workspace() -> None:
    clear_vector_store()
    if UPLOADS_DIR.exists():
        for path in UPLOADS_DIR.iterdir():
            if path.is_file() and path.name != ".gitkeep":
                path.unlink()
    st.session_state.pop("last_output", None)
    st.session_state.pop("last_format", None)
    st.session_state["vector_store"] = None


# Save files, chunk, embed, merge into FAISS. Returns (chunk_count, error_or_none).
def process_uploaded_files(uploaded_files) -> tuple[int, str | None]:
    if not uploaded_files:
        return 0, "No files selected."

    all_docs: list[Document] = []
    for uf in uploaded_files:
        suffix = Path(uf.name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return 0, f"Unsupported type for {uf.name!r}. Only PDF and DOCX are allowed."

        dest = UPLOADS_DIR / uf.name
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

    try:
        existing = load_vector_store()
        store = build_or_merge_store(all_docs, existing=existing)
        save_vector_store(store)
    except Exception as exc:
        return 0, f"Indexing failed: {_friendly_error(exc)}"

    st.session_state["vector_store"] = store
    return len(all_docs), None


def main() -> None:
    st.set_page_config(
        page_title="Agentic Knowledge Workspace",
        page_icon="📚",
        layout="wide",
    )

    st.title("Agentic Knowledge Workspace")
    st.caption(
        "Upload documents, index them locally, and ask focused questions "
        "with RAG + Gemini — answers grounded in the most relevant passages."
    )

    with st.sidebar:
        st.subheader("Workspace")
        st.text(f"Uploads: {UPLOADS_DIR}")
        st.text(f"Vector DB: {DEFAULT_INDEX_DIR}")
        if st.button("Reload index from disk"):
            _invalidate_store_cache()
            st.success("Cache cleared. Index will reload on next action.")
        if st.button("Try again (clear database)", type="secondary"):
            clear_workspace()
            st.success("Vector database and uploads cleared. Start with new documents.")
            st.rerun()
        st.divider()
        st.markdown(
            "**Tip:** Process files after each upload batch. "
            "New chunks are merged into your local FAISS index."
        )

    col_u, col_q = st.columns((1, 1), gap="large")

    with col_u:
        st.subheader("1. Document upload")
        st.info(
            "Starting a new set of documents? Click 'Try again (clear database)' first "
            "to avoid mixing vectors from older uploads."
        )
        uploaded = st.file_uploader(
            "PDF or DOCX",
            type=["pdf", "docx"],
            accept_multiple_files=True,
            help="Files are stored under the local uploads/ folder.",
        )

        if st.button("Process uploaded documents", type="primary"):
            with st.spinner("Extracting text, chunking, embedding, and updating FAISS…"):
                count, err = process_uploaded_files(uploaded)
            if err:
                st.error(err)
            else:
                st.success(f"Indexed {count} chunk(s) successfully.")

        st.subheader("Processing status")
        store = _get_store()
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

        b1, b2 = st.columns([1, 1])
        with b1:
            do_generate = st.button("Generate", type="primary", use_container_width=True)
        with b2:
            do_try_again = st.button(
                "Try again (clear database)",
                use_container_width=True,
                help="Deletes the FAISS index, uploaded files, and last output so you can start fresh.",
            )

        st.subheader("3. Generated output")
        output_placeholder = st.container()

        if do_try_again:
            clear_workspace()
            st.success("Vector database and uploads cleared. Upload and process new documents.")
            st.rerun()

        if do_generate:
            store = _get_store()
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
