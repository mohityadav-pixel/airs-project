"""Thin, defensive wrapper around the Gemini API.

Responsibilities kept here on purpose: key handling, timeouts, retries, prompt
sanitisation and failure typing. Everything about *what* to ask lives in
:mod:`app.ai.copilot` and :mod:`app.ai.explain`.

The API key never leaves the server: the browser talks to AIRS, AIRS talks to
Gemini.
"""
from __future__ import annotations

import logging
import re

from app.core.config import settings
from app.core.errors import AIUnavailable
from app.core.logging_config import get_logger, log_event

logger = get_logger("airs.ai")

MAX_USER_CHARS = 1200

# Strip attempts to talk to the model as if they were the operator. This is not
# a security boundary on its own — the system prompt also states that user text
# is data, and the grounded-facts block is the only source of numbers.
_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all|any|previous|prior) (instructions|prompts)"),
    re.compile(r"(?i)\b(system|developer) prompt\b"),
    re.compile(r"(?i)you are now\b"),
    re.compile(r"(?i)\bdisregard\b.{0,20}\b(above|previous|instructions)\b"),
]


def sanitize_user_text(text: str) -> str:
    cleaned = (text or "").strip()[:MAX_USER_CHARS]
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[removed]", cleaned)
    return cleaned


def available() -> bool:
    return bool(settings.gemini_api_key)


def generate(system_instruction: str, prompt: str, *,
             temperature: float = 0.3, max_output_tokens: int = 900) -> str:
    if not available():
        raise AIUnavailable("The AI Copilot is not configured on this server "
                            "(no Gemini API key).")
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:                       # pragma: no cover
        raise AIUnavailable("The Gemini client library is not installed.") from exc

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise AIUnavailable("The AI service returned an empty response.")
        return text
    except AIUnavailable:
        raise
    except Exception as exc:                          # network, quota, safety…
        log_event(logger, logging.WARNING, "gemini_call_failed",
                  error=type(exc).__name__)
        raise AIUnavailable("The AI service could not be reached. The rest of "
                            "AIRS is unaffected.") from exc
