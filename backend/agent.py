# Lightweight RAG orchestration: instruction → retrieve → generate.

from typing import Literal

from langchain_community.vectorstores import FAISS

from backend.generator import ResponseFormat, generate_rag_output
from backend.retriever import DEFAULT_K, format_context, retrieve_context

VALID_FORMATS = frozenset({"answer", "brief_summary", "extract", "compare"})


def run_agent(
    store: FAISS,
    user_instruction: str,
    response_format: ResponseFormat = "answer",
    top_k: int = DEFAULT_K,
) -> tuple[str, ResponseFormat]:
    instruction = (user_instruction or "").strip()
    if not instruction:
        raise ValueError("Enter a question or instruction before generating.")

    if response_format not in VALID_FORMATS:
        raise ValueError(f"Unknown response format: {response_format!r}")

    docs = retrieve_context(store, instruction, k=top_k)
    context = format_context(docs)
    output = generate_rag_output(
        response_format, context=context, instruction=instruction
    )
    return output, response_format
