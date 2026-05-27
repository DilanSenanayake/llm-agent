# Gemini generation via the Google Gen AI SDK (google.genai).

import os
from typing import Literal

from google import genai
from google.genai.types import GenerateContentConfig

IntentType = Literal["ask", "summary", "report", "slides", "compare"]

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


ASK_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
Answer the user's question directly and concisely.
If the context is insufficient, say what is missing instead of inventing facts.
Use markdown where helpful (headings, lists, bold for emphasis)."""


SUMMARY_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
If the context is insufficient, say what is missing instead of inventing facts.
Produce markdown with:
## Concise Summary
## Key Points
## Important Insights
Keep the tone clear and professional."""


REPORT_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
Synthesize across chunks; do not invent sources or facts not supported by the context.
Produce markdown with exactly these sections:
## Introduction
## Main Findings
## Analysis
## Conclusion
Maintain coherence and professional tone."""


SLIDES_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
If the context is insufficient, say what is missing instead of inventing facts.
Produce a slide deck outline in markdown. For each slide use:
### Slide N: Title
- Bullet points (3–5 per slide, concise)
Include a title slide and a closing slide. Keep content presentation-ready."""


COMPARE_SYSTEM = """You are a careful analyst. You ONLY use the RETRIEVED CONTEXT below.
If the context is insufficient, say what is missing instead of inventing facts.
Produce markdown with:
## Overview
## Comparison Table (use markdown table when possible)
## Key Similarities
## Key Differences
## Conclusion
Be balanced and cite only what the context supports."""


_SYSTEM_BY_INTENT: dict[IntentType, str] = {
    "ask": ASK_SYSTEM,
    "summary": SUMMARY_SYSTEM,
    "report": REPORT_SYSTEM,
    "slides": SLIDES_SYSTEM,
    "compare": COMPARE_SYSTEM,
}

USER_TEMPLATE = """RETRIEVED CONTEXT:
{context}

USER INSTRUCTION:
{instruction}

Generate the requested output following the system rules. Use markdown."""


def generate_rag_output(
    intent: IntentType,
    context: str,
    instruction: str,
) -> str:
    system = _SYSTEM_BY_INTENT[intent]
    user_content = USER_TEMPLATE.format(
        context=context.strip(),
        instruction=(instruction or "").strip() or "Follow the system format.",
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
