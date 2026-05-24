# FAISS vector store persistence and document indexing.

import shutil
from pathlib import Path
from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from backend.paths import DEFAULT_INDEX_DIR


# Lazy import so app startup does not load sentence-transformers immediately.
def _get_embeddings():
    from backend.embeddings import get_embeddings

    return get_embeddings()


# Load FAISS index from disk if it exists.
def load_vector_store(index_dir: Optional[Path] = None) -> Optional[FAISS]:
    index_dir = index_dir or DEFAULT_INDEX_DIR
    if not index_dir.exists():
        return None
    try:
        return FAISS.load_local(
            str(index_dir),
            _get_embeddings(),
            allow_dangerous_deserialization=True,
        )
    except Exception:
        return None


def save_vector_store(store: FAISS, index_dir: Optional[Path] = None) -> None:
    index_dir = index_dir or DEFAULT_INDEX_DIR
    index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(index_dir))


# Create a new FAISS index or merge documents into an existing one.
def build_or_merge_store(
    documents: List[Document],
    existing: Optional[FAISS] = None,
) -> FAISS:
    embeddings = _get_embeddings()
    if not documents:
        raise ValueError("No document chunks to index.")

    if existing is None:
        return FAISS.from_documents(documents, embeddings)

    existing.add_documents(documents)
    return existing


# Remove persisted FAISS index from disk.
def clear_vector_store(index_dir: Optional[Path] = None) -> None:
    index_dir = index_dir or DEFAULT_INDEX_DIR
    if index_dir.exists():
        shutil.rmtree(index_dir)
