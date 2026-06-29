# Lightweight RAG orchestration: instruction → retrieve → generate.

from collections.abc import Iterator
from typing import Literal

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from backend.chat_history import format_chat_history
from backend.generator import ResponseFormat, generate_rag_output, stream_rag_output
from backend.retriever import DEFAULT_K, format_context, retrieve_context

VALID_FORMATS = frozenset({"answer", "brief_summary", "extract", "compare"})
FormatChoice = ResponseFormat | Literal["auto"]


def detect_response_format(user_text: str) -> ResponseFormat:
    """Keyword-based format detection when the user selects Auto."""
    t = (user_text or "").lower()

    if any(k in t for k in ["compare", "difference", "vs", "versus", "contrast"]):
        return "compare"

    if any(
        k in t
        for k in [
            "extract",
            "list all",
            "list the",
            "bullet",
            "table of",
            "find all",
            "pull out",
        ]
    ):
        return "extract"

    if any(k in t for k in ["summarize", "summary", "tldr", "brief", "overview"]):
        return "brief_summary"

    return "answer"


def resolve_response_format(
    user_instruction: str,
    choice: FormatChoice,
) -> ResponseFormat:
    if choice != "auto":
        return choice
    return detect_response_format(user_instruction)


def format_citations(docs: list[Document]) -> str:
    sources: list[str] = []
    seen: set[str] = set()
    for doc in docs:
        src = doc.metadata.get("source", "unknown")
        if src not in seen:
            seen.add(src)
            sources.append(src)
    if not sources:
        return ""
    joined = " · ".join(f"`{name}`" for name in sources)
    return f"\n\n---\n**Sources:** {joined}"


def prepare_rag(
    store: FAISS,
    user_instruction: str,
    response_format: FormatChoice = "auto",
    chat_messages: list[dict] | None = None,
    top_k: int = DEFAULT_K,
) -> tuple[ResponseFormat, str, list[Document], str]:
    instruction = (user_instruction or "").strip()
    if not instruction:
        raise ValueError("Enter a question or instruction before generating.")

    fmt = resolve_response_format(instruction, response_format)
    if fmt not in VALID_FORMATS:
        raise ValueError(f"Unknown response format: {fmt!r}")

    docs = retrieve_context(store, instruction, k=top_k)
    context = format_context(docs)
    history = format_chat_history(chat_messages or [])
    return fmt, context, docs, history


def run_agent(
    store: FAISS,
    user_instruction: str,
    response_format: FormatChoice = "auto",
    chat_messages: list[dict] | None = None,
    top_k: int = DEFAULT_K,
) -> tuple[str, ResponseFormat]:
    fmt, context, docs, history = prepare_rag(
        store,
        user_instruction,
        response_format=response_format,
        chat_messages=chat_messages,
        top_k=top_k,
    )
    output = generate_rag_output(
        fmt,
        context=context,
        instruction=user_instruction,
        chat_history=history,
    )
    citations = format_citations(docs)
    if citations and citations not in output:
        output = output + citations
    return output, fmt


def stream_agent(
    store: FAISS,
    user_instruction: str,
    response_format: FormatChoice = "auto",
    chat_messages: list[dict] | None = None,
    top_k: int = DEFAULT_K,
) -> tuple[Iterator[str], ResponseFormat, list[Document]]:
    fmt, context, docs, history = prepare_rag(
        store,
        user_instruction,
        response_format=response_format,
        chat_messages=chat_messages,
        top_k=top_k,
    )

    def _stream() -> Iterator[str]:
        for chunk in stream_rag_output(
            fmt,
            context=context,
            instruction=user_instruction,
            chat_history=history,
        ):
            yield chunk
        citations = format_citations(docs)
        if citations:
            yield citations

    return _stream(), fmt, docs
