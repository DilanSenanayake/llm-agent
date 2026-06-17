# Lightweight RAG orchestration: instruction → retrieve → generate.

from typing import Literal

from langchain_community.vectorstores import FAISS

from backend.generator import ResponseFormat, generate_rag_output
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


def run_agent(
    store: FAISS,
    user_instruction: str,
    response_format: FormatChoice = "auto",
    top_k: int = DEFAULT_K,
) -> tuple[str, ResponseFormat]:
    instruction = (user_instruction or "").strip()
    if not instruction:
        raise ValueError("Enter a question or instruction before generating.")

    fmt = resolve_response_format(instruction, response_format)
    if fmt not in VALID_FORMATS:
        raise ValueError(f"Unknown response format: {fmt!r}")

    docs = retrieve_context(store, instruction, k=top_k)
    context = format_context(docs)
    output = generate_rag_output(fmt, context=context, instruction=instruction)
    return output, fmt
