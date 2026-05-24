# Gemini generation via the Google Gen AI SDK (google.genai).

import os
from typing import Literal

from google import genai
from google.genai.types import GenerateContentConfig

IntentType = Literal["summary", "report"]

DEFAULT_MODEL = "gemini-3-flash-preview"
MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
)


# API key from GEMINI_API_KEY (or GOOGLE_API_KEY) per Google Gen AI SDK.
def _get_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if key:
        return genai.Client(api_key=key)
    # Client() also reads GEMINI_API_KEY from the environment when api_key is omitted
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


USER_TEMPLATE = """RETRIEVED CONTEXT:
{context}

USER INSTRUCTION:
{instruction}

Generate the requested output following the system rules. Use markdown."""


# Call Gemini with system instruction + user content (RAG context).
def generate_rag_output(
    intent: IntentType,
    context: str,
    instruction: str,
) -> str:
    system = SUMMARY_SYSTEM if intent == "summary" else REPORT_SYSTEM
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
