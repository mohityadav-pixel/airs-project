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

from app.core import cache as cache_module
from app.core.config import settings
from app.core.errors import AIUnavailable
from app.core.logging_config import get_logger, log_event

logger = get_logger("airs.ai")

MAX_USER_CHARS = 1200

# Strip attempts to talk to the model as if they were the operator. This is not
# a security boundary on its own — the system prompt also states that user text
# is data, and the grounded-facts block is the only source of numbers.
# Defence in depth, not the security boundary: the system prompt already
# states that user text is data and that no figure may come from outside the
# grounded facts. This just removes the most common override attempts before
# they reach the model.
#
# The earlier pattern required "ignore" to be followed immediately by
# "instructions" or "prompts", so the single most common phrasing — "ignore all
# previous instructions" — sailed straight through. Filler words between the
# verb and the noun are now allowed for.
_INJECTION_PATTERNS = [
    re.compile(r"(?i)\b(ignore|disregard|forget|override)\b"
               r"(?:\W+\w+){0,4}?\W+"
               r"\b(instructions?|prompts?|rules?|directions?|guidelines?)\b"),
    re.compile(r"(?i)\b(system|developer|initial|original)\s+prompt\b"),
    re.compile(r"(?i)\byou are now\b"),
    re.compile(r"(?i)\bact as (?:if you are )?(?:an? )?(?:unrestricted|"
               r"jailbroken|different)\b"),
    re.compile(r"(?i)\breveal\b(?:\W+\w+){0,3}?\W+"
               r"\b(prompt|instructions?|rules?)\b"),
]


def sanitize_user_text(text: str) -> str:
    cleaned = (text or "").strip()[:MAX_USER_CHARS]
    for pattern in _INJECTION_PATTERNS:
        cleaned = pattern.sub("[removed]", cleaned)
    return cleaned


def available() -> bool:
    return bool(settings.gemini_api_key)


# Google retires model IDs on a rolling basis, and a retired ID fails with the
# same opaque error as a bad key. Rather than leave the assistant dead until
# someone edits .env, try the configured model first and then a short list of
# current alternatives — and remember which one worked, so the fallback costs
# one extra call once rather than on every message.
FALLBACK_MODELS = [
    "gemini-2.5-flash",       # current workhorse
    "gemini-flash-latest",    # always points at the newest flash
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",       # retired for newer keys, kept for older ones
    "gemini-1.5-flash",
]

_working_model: str | None = None


def _model_candidates() -> list[str]:
    if _working_model:
        return [_working_model]
    ordered = [settings.gemini_model]
    ordered += [m for m in FALLBACK_MODELS if m != settings.gemini_model]
    return ordered


def _is_model_problem(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(hint in text for hint in
               ("not found", "not_found", "404", "is not supported",
                "unsupported", "deprecated", "does not exist"))


def generate(system_instruction: str, prompt: str, *,
             temperature: float = 0.3, max_output_tokens: int = 900) -> str:
    global _working_model

    if not available():
        raise AIUnavailable("The AI Copilot is not configured on this server "
                            "(no Gemini API key).")
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:                       # pragma: no cover
        raise AIUnavailable("The Gemini client library is not installed.") from exc

    client = genai.Client(api_key=settings.gemini_api_key)

    def build_config(*, budget: int, no_thinking: bool):
        """Assemble the request config.

        `max_output_tokens` on a Gemini 2.5-class model covers the model's
        internal reasoning as well as the visible reply, so a budget sized for
        the answer alone gets eaten by thinking and the reply is truncated
        mid-sentence. These are short grounded explanations — the reasoning is
        already done by AIRS — so thinking is switched off where the model
        supports it, which removes the truncation and the latency together.
        """
        kwargs = {
            "system_instruction": system_instruction,
            "temperature": temperature,
            "max_output_tokens": budget,
        }
        if no_thinking:
            try:
                kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            except Exception:                      # older SDK, no such field
                pass
        return types.GenerateContentConfig(**kwargs)

    def was_truncated(response) -> bool:
        try:
            reason = str(response.candidates[0].finish_reason or "")
        except (AttributeError, IndexError, TypeError):
            return False
        return "MAX_TOKENS" in reason.upper()

    last_exc: BaseException | None = None
    for model in _model_candidates():
        try:
            attempts = [
                {"budget": max_output_tokens, "no_thinking": True},
                # Some models reject thinking_config outright; others ignore the
                # zero budget and still reason. Either way, retry with room for
                # both rather than returning half a sentence.
                {"budget": max_output_tokens * 4, "no_thinking": False},
            ]
            response = None
            for index, attempt in enumerate(attempts):
                try:
                    response = client.models.generate_content(
                        model=model, contents=prompt,
                        config=build_config(**attempt))
                except Exception as call_exc:
                    if index == 0 and "thinking" in str(call_exc).lower():
                        log_event(logger, logging.INFO, "gemini_thinking_unsupported",
                                  model=model)
                        continue
                    raise
                if not was_truncated(response):
                    break
                log_event(logger, logging.WARNING, "gemini_response_truncated",
                          model=model, budget=attempt["budget"],
                          next_step="retrying with a larger budget"
                                    if index == 0 else "giving up")

            text = (response.text or "").strip() if response is not None else ""
            if not text:
                raise AIUnavailable("The AI service returned an empty response.")
            if _working_model != model:
                log_event(logger, logging.INFO, "gemini_model_selected",
                          model=model, configured=settings.gemini_model)
                _working_model = model
            cache_module.record_success("gemini")
            return text
        except AIUnavailable:
            raise
        except Exception as exc:
            last_exc = exc
            if _is_model_problem(exc):
                # Wrong or retired model ID — try the next candidate.
                log_event(logger, logging.WARNING, "gemini_model_unavailable",
                          model=model, detail=str(exc)[:200])
                continue
            # A key, quota or network problem will not be fixed by another
            # model name, so stop here.
            break

    # Every candidate failed. The class name alone ("ClientError") is useless
    # for diagnosis, so the real message goes to the log and into the error
    # detail — never into the user-facing message, which must not leak a key.
    exc = last_exc or RuntimeError("no Gemini model could be reached")
    log_event(logger, logging.WARNING, "gemini_call_failed",
              error=type(exc).__name__, detail=str(exc)[:400],
              configured_model=settings.gemini_model)
    cache_module.record_failure("gemini", exc)
    raise AIUnavailable(
        "The AI assistant could not be reached. Run "
        "`.venv/bin/python -m scripts.check_providers` to see why — the rest "
        "of AIRS is unaffected.",
        detail=f"{type(exc).__name__}: {exc}") from exc
