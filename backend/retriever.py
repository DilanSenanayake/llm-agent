# Retrieve relevant chunks from the FAISS vector store.

from typing import List, Optional

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS


DEFAULT_K = 8


# Return up to `k` similar documents for the query.
#
# Raises:
#     ValueError: On empty query or retrieval failure.
def retrieve_context(
    store: FAISS,
    query: str,
    k: int = DEFAULT_K,
) -> List[Document]:
    q = (query or "").strip()
    if not q:
        raise ValueError("Query is empty; enter an instruction or topic.")

    try:
        docs = store.similarity_search(q, k=k)
    except Exception as exc:
        raise ValueError(f"Retrieval failed: {exc}") from exc

    if not docs:
        raise ValueError(
            "No relevant chunks were found. Try rephrasing or process documents first."
        )
    return docs


# Join retrieved chunks into a single context block for the LLM.
def format_context(docs: List[Document], max_chars: Optional[int] = 12000) -> str:
    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        src = doc.metadata.get("source", "unknown")
        parts.append(f"[Chunk {i} | source: {src}]\n{doc.page_content}")

    text = "\n\n---\n\n".join(parts)
    if max_chars and len(text) > max_chars:
        text = text[:max_chars] + "\n\n[Context truncated for length.]"
    return text
