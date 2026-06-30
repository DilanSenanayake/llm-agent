from __future__ import annotations

from typing import Literal

from backend.generator import ResponseFormat

FORMAT_OPTIONS: dict[str, ResponseFormat | Literal["auto"]] = {
    "Auto": "auto",
    "Answer": "answer",
    "Brief summary": "brief_summary",
    "Extract": "extract",
    "Compare": "compare",
}

FORMAT_LABELS = {v: k for k, v in FORMAT_OPTIONS.items()}

FORMAT_DESCRIPTIONS: dict[str, str] = {
    "Auto": "Picks a format from keywords in your message.",
    "Answer": "Direct answer to a specific question.",
    "Brief summary": "Short overview of the topic you name.",
    "Extract": "Bullets, tables, or key facts only.",
    "Compare": "Side-by-side — name both items in your message.",
}

SUGGESTED_PROMPTS: list[dict[str, str | ResponseFormat]] = [
    {"format": "answer", "prompt": "Main risks?"},
    {"format": "brief_summary", "prompt": "Key themes"},
    {"format": "extract", "prompt": "Deadlines & requirements"},
    {"format": "compare", "prompt": "Methodology vs findings"},
]

SESSION_QP = "sid"
