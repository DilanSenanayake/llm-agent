# Lightweight RAG orchestration: intent → retrieve → generate.

from typing import Literal, Optional

from langchain_community.vectorstores import FAISS

from backend.generator import generate_rag_output
from backend.retriever import DEFAULT_K, format_context, retrieve_context

IntentResult = Literal["summary", "report"]

# 'correct the intent detection to be more accurate'

# from typing import Optional

# Intent = str  # "ask", "summary", "report", "slides", "compare"

# VALID_INTENTS = {"ask", "summary", "report", "slides", "compare"}

# def detect_intent(user_text: str, forced: Optional[Intent] = None) -> Intent:
#     """
#     Hybrid intent detection:
#     1. UI forced intent (highest priority)
#     2. Lightweight semantic fallback
#     3. Safe default = summary
#     """

#     # 1. UI override (authoritative)
#     if forced in VALID_INTENTS:
#         return forced

#     t = (user_text or "").lower()

#     # 2. Lightweight rules (ONLY for fallback cases)
#     if any(k in t for k in ["compare", "difference", "vs", "versus"]):
#         return "compare"

#     if any(k in t for k in ["slides", "presentation", "ppt"]):
#         return "slides"

#     if any(k in t for k in ["report", "detailed report", "structured report"]):
#         return "report"

#     if any(k in t for k in ["summarize", "summary", "tldr", "brief"]):
#         return "summary"

#     if any(k in t for k in ["ask", "question", "what", "how", "why"]):
#         return "ask"

#     # 3. Default fallback
#     return "summary"



# Simple keyword-based intent. `forced` overrides when UI sends explicit mode.
#
# Priority when not forced: 'report' if 'report' in text, else 'summary' if
# 'summary' in text, else default summary.
def detect_intent(user_text: str, forced: Optional[IntentResult] = None) -> IntentResult:
    if forced:
        return forced
    t = (user_text or "").lower()
    if "report" in t:
        return "report"
    if "summary" in t:
        return "summary"
    return "summary"


# Full RAG pipeline: classify intent, retrieve chunks, generate markdown output.
#
# Returns:
#     (markdown_output, resolved_intent)
def run_agent(
    store: FAISS,
    user_instruction: str,
    forced_intent: Optional[IntentResult] = None,
    top_k: int = DEFAULT_K,
) -> tuple[str, IntentResult]:
    intent = detect_intent(user_instruction, forced=forced_intent)
    retrieval_query = (user_instruction or "").strip()
    if not retrieval_query:
        retrieval_query = (
            "Key themes, definitions, and conclusions across the documents."
            if intent == "summary"
            else "Facts, sections, and evidence suitable for a structured report."
        )
    docs = retrieve_context(store, retrieval_query, k=top_k)
    context = format_context(docs)
    output = generate_rag_output(intent, context=context, instruction=user_instruction)
    return output, intent
