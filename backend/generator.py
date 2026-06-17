# Gemini generation via the Google Gen AI SDK (google.genai).

import os
from typing import Literal

from google import genai
from google.genai.types import GenerateContentConfig

ResponseFormat = Literal["answer", "brief_summary", "extract", "compare"]

DEFAULT_MODEL = "gemini-3-flash-preview"
MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
)


def _get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return genai.Client(api_key=key)
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError(
            "Missing API key. Set GEMINI_API_KEY in your environment or .env file."
        )
    return genai.Client()


def _model_candidates() -> list[str]:
    primary = (os.getenv("GEMINI_MODEL") or DEFAULT_MODEL).strip()
    ordered: list[str] = []
    for name in (primary, *MODEL_FALLBACKS):
        if name and name not in ordered:
            ordered.append(name)
    return ordered


def _is_model_not_found(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "not_found" in msg or "404" in msg


ANSWER_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
Answer the user's question directly and concisely.
If the context is insufficient, say what is missing instead of inventing facts.
Use markdown where helpful (headings, lists, bold for emphasis)."""


BRIEF_SUMMARY_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
If the context is insufficient, say what is missing instead of inventing facts.
Produce a short overview of the topic named in the user instruction — not a full document review.
Use markdown with:
## Summary
## Key Points (3–7 bullets)
Keep the tone clear and professional."""


EXTRACT_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
If the context is insufficient, say what is missing instead of inventing facts.
Extract only the facts, items, or data the user asked for — no narrative essay.
Prefer bullets, numbered lists, or markdown tables. Include dates, names, numbers, and
requirements when present. Do not pad with commentary."""


COMPARE_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
If the context is insufficient, say what is missing instead of inventing facts.
Compare only what the user named in their instruction.
Produce markdown with:
## Overview
## Comparison Table (use a markdown table when possible)
## Key Similarities
## Key Differences
## Conclusion
Be balanced and cite only what the context supports."""


_SYSTEM_BY_FORMAT: dict[ResponseFormat, str] = {
    "answer": ANSWER_SYSTEM,
    "brief_summary": BRIEF_SUMMARY_SYSTEM,
    "extract": EXTRACT_SYSTEM,
    "compare": COMPARE_SYSTEM,
}

USER_TEMPLATE = """RETRIEVED CONTEXT:
{context}

USER INSTRUCTION:
{instruction}

Generate the requested output following the system rules. Use markdown."""


def generate_rag_output(
    response_format: ResponseFormat,
    context: str,
    instruction: str,
) -> str:
    system = _SYSTEM_BY_FORMAT[response_format]
    user_content = USER_TEMPLATE.format(
        context=context.strip(),
        instruction=instruction.strip(),
    )

    client = _get_client()
    last_exc: Exception | None = None
    tried: list[str] = []

    for model_name in _model_candidates():
        tried.append(model_name)
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_content,
                config=GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.2,
                ),
            )
            text = (response.text or "").strip()
            if text:
                return text
            raise RuntimeError("The model returned an empty response. Try again.")
        except Exception as exc:
            last_exc = exc
            if not _is_model_not_found(exc):
                raise RuntimeError(f"Gemini API error: {exc}") from exc

    raise RuntimeError(
        f"Gemini API error: no available model. Tried: {', '.join(tried)}. "
        f"Last error: {last_exc}. Set GEMINI_MODEL in .env (e.g. gemini-3-flash-preview). "
        "See https://ai.google.dev/gemini-api/docs/models"
    ) from last_exc
