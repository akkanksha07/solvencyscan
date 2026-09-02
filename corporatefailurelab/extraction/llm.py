"""Thin wrapper around the Anthropic client (mirrors AuditIQ's intelligence/llm.py)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from ..config import settings


class LLMError(RuntimeError):
    """Raised when the LLM is unavailable or misconfigured."""


@lru_cache(maxsize=1)
def get_client():
    if not settings.has_api_key:
        raise LLMError(
            "ANTHROPIC_API_KEY is not set -- add it to a .env file in the project "
            "root to enable the PDF upload feature."
        )
    from anthropic import Anthropic

    return Anthropic(api_key=settings.anthropic_api_key)


def _text_from(resp) -> str:
    return "\n".join(b.text for b in resp.content if getattr(b, "type", None) == "text").strip()


def complete(prompt: str, *, max_tokens: int = 4000) -> str:
    client = get_client()
    resp = client.messages.create(
        model=settings.extraction_model,
        max_tokens=max_tokens,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    return _text_from(resp)


def extract_json(text: str) -> Any:
    """Parse a JSON value from a model response, tolerating fences / prose."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise
