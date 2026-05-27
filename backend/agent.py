# Lightweight RAG orchestration: intent → retrieve → generate.

from typing import Literal, Optional

from langchain_community.vectorstores import FAISS

from backend.generator import generate_rag_output
from backend.retriever import DEFAULT_K, format_context, retrieve_context

IntentResult = Literal["ask", "summary", "report", "slides", "compare"]

VALID_INTENTS = frozenset({"ask", "summary", "report", "slides", "compare"})

_DEFAULT_RETRIEVAL: dict[IntentResult, str] = {
    "ask": "Key facts, definitions, and answers across the documents.",
    "summary": "Key themes, definitions, and conclusions across the documents.",
    "report": "Facts, sections, and evidence suitable for a structured report.",
    "slides": "Main topics, headings, and bullet-worthy points across the documents.",
    "compare": "Similarities, differences, and contrasting points across the documents.",
}


def detect_intent(user_text: str, forced: Optional[IntentResult] = None) -> IntentResult:
    """
    Hybrid intent detection:
    1. UI forced intent (highest priority)
    2. Lightweight keyword fallback
    3. Safe default = ask
    """
    if forced in VALID_INTENTS:
        return forced

    t = (user_text or "").lower()

    if any(k in t for k in ["compare", "difference", "vs", "versus", "contrast"]):
        return "compare"

    if any(k in t for k in ["slides", "presentation", "ppt", "deck"]):
        return "slides"

    if any(k in t for k in ["report", "detailed report", "structured report"]):
        return "report"

    if any(k in t for k in ["summarize", "summary", "tldr", "brief", "overview"]):
        return "summary"

    # Default: treat as a direct question
    return "ask"


def run_agent(
    store: FAISS,
    user_instruction: str,
    forced_intent: Optional[IntentResult] = None,
    top_k: int = DEFAULT_K,
) -> tuple[str, IntentResult]:
    intent = detect_intent(user_instruction, forced=forced_intent)
    retrieval_query = (user_instruction or "").strip()
    if not retrieval_query:
        retrieval_query = _DEFAULT_RETRIEVAL[intent]
    docs = retrieve_context(store, retrieval_query, k=top_k)
    context = format_context(docs)
    output = generate_rag_output(intent, context=context, instruction=user_instruction)
    return output, intent
