# Uploaded document listing, indexing, and removal.

from pathlib import Path

from langchain_core.documents import Document

from backend.chunker import chunk_text
from backend.document_loader import SUPPORTED_EXTENSIONS, load_document
from backend.storage import check_upload_capacity
from backend.users import get_user_index_dir, get_user_uploads_dir
from backend.vector_store import (
    build_or_merge_store,
    clear_vector_store,
    load_vector_store,
    save_vector_store,
)


def list_uploaded_documents(user_id: str) -> list[dict]:
    uploads_dir = get_user_uploads_dir(user_id)
    if not uploads_dir.exists():
        return []
    docs: list[dict] = []
    for path in sorted(uploads_dir.iterdir()):
        if path.is_file() and path.name != ".gitkeep":
            docs.append({"name": path.name, "size": path.stat().st_size})
    return docs


def _index_file(path: Path) -> list[Document]:
    text = load_document(path)
    chunks = chunk_text(text, chunk_size_words=500, overlap_words=50)
    if not chunks:
        raise ValueError(f"No chunks produced from {path.name} (empty after processing).")
    return [
        Document(
            page_content=chunk,
            metadata={"source": path.name, "chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
    ]


def rebuild_vector_store(user_id: str):
    uploads_dir = get_user_uploads_dir(user_id)
    index_dir = get_user_index_dir(user_id)
    all_docs: list[Document] = []

    if uploads_dir.exists():
        for path in sorted(uploads_dir.iterdir()):
            if not path.is_file() or path.name == ".gitkeep":
                continue
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            all_docs.extend(_index_file(path))

    if not all_docs:
        clear_vector_store(index_dir)
        return None

    store = build_or_merge_store(all_docs, existing=None)
    save_vector_store(store, index_dir)
    return store


def remove_uploaded_documents(user_id: str, filenames: set[str]) -> str | None:
    """Remove files from disk and rebuild the vector index."""
    if not filenames:
        return None
    uploads_dir = get_user_uploads_dir(user_id)
    try:
        for name in filenames:
            path = uploads_dir / name
            if path.exists():
                path.unlink()
        rebuild_vector_store(user_id)
    except Exception as exc:
        return f"Could not remove document(s): {exc}"
    return None


def indexed_file_names(user_id: str) -> set[str]:
    return {doc["name"] for doc in list_uploaded_documents(user_id)}


def process_uploaded_files(
    uploaded_files,
    user_id: str,
) -> tuple[list[str], int, str | None]:
    if not uploaded_files:
        return [], 0, None

    incoming = [(uf.name, len(uf.getvalue())) for uf in uploaded_files]
    ok, err = check_upload_capacity(user_id, incoming)
    if not ok:
        return [], 0, err

    saved_names: list[str] = []
    chunk_count = 0
    uploads_dir = get_user_uploads_dir(user_id)
    uploads_dir.mkdir(parents=True, exist_ok=True)

    for uf in uploaded_files:
        suffix = Path(uf.name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            return [], 0, f"Unsupported type for {uf.name!r}. Only PDF and DOCX are allowed."

        dest = uploads_dir / uf.name
        dest.write_bytes(uf.getvalue())
        saved_names.append(uf.name)

    try:
        store = rebuild_vector_store(user_id)
    except ValueError as exc:
        return [], 0, str(exc)
    except Exception as exc:
        return [], 0, f"Indexing failed: {exc}"

    if store is not None:
        chunk_count = store.index.ntotal  # type: ignore[attr-defined]

    return saved_names, chunk_count, None


def remove_document(user_id: str, filename: str) -> str | None:
    uploads_dir = get_user_uploads_dir(user_id)
    path = uploads_dir / filename
    if not path.exists():
        return f"Document {filename!r} not found."
    try:
        path.unlink()
        rebuild_vector_store(user_id)
    except Exception as exc:
        return f"Could not remove {filename}: {exc}"
    return None
