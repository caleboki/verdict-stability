"""Thin, stateless wrappers around each provider.

Every call is a fresh, single turn request with no conversation history, so a
run cannot see or copy any earlier answer. Each wrapper returns a Reply: the
visible text plus what the provider reports about the call (the model that
actually served it, why it stopped, and token counts).

Retries live in run_experiment.one_call, so the SDKs' own retries are switched
off to keep a single retry policy.
"""

from __future__ import annotations

import hashlib
import os
import random
from dataclasses import dataclass

# Stop reasons meaning the answer hit max_tokens before it finished.
TRUNCATION_REASONS = {"max_tokens", "length", "MAX_TOKENS"}


@dataclass
class Reply:
    text: str
    served_model: str | None = None
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    # Hidden reasoning blocks in the response. Newer models think by default,
    # which can change both the scores and their spread.
    thinking_blocks: int | None = None
    # On a refusal, the policy category the API reports (for example "cyber"),
    # which separates a safety filter blocking the request from the model declining.
    refusal_category: str | None = None


class TemperatureUnsupported(Exception):
    """The model rejected an explicit temperature setting."""


def _looks_like_temperature_error(exc: Exception) -> bool:
    """Only called for a 400 on a request that set a temperature, so any
    mention of temperature in the message means the model refused it. The
    exact wording varies by provider and model, so no further match is needed."""
    return "temperature" in str(exc).lower()


def is_retryable(exc: Exception) -> bool:
    """Rate limits, server errors and connection problems are worth retrying.

    Other client errors (a retired model ID, a bad parameter, a missing key)
    fail the same way every time, so retrying them only wastes time.
    """
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)  # google-genai puts the HTTP status here
    if isinstance(status, int):
        return status == 429 or status >= 500
    name = type(exc).__name__.lower()
    return "connect" in name or "timeout" in name


def call_anthropic(model: str, prompt: str, temperature: float | None, max_tokens: int) -> Reply:
    import anthropic

    client = anthropic.Anthropic(max_retries=0)  # reads ANTHROPIC_API_KEY
    kwargs = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if temperature is not None:
        # The 1.x SDK removed `temperature` from its signature, but the API
        # still honours it on older models; newer ones reject it with a 400.
        kwargs["extra_body"] = {"temperature": temperature}
    try:
        resp = client.messages.create(**kwargs)
    except anthropic.BadRequestError as exc:
        if temperature is not None and _looks_like_temperature_error(exc):
            raise TemperatureUnsupported(str(exc)) from exc
        raise
    usage = getattr(resp, "usage", None)
    types = [getattr(block, "type", None) for block in resp.content]
    # stop_details is informational and may be missing even on a refusal.
    stop_details = getattr(resp, "stop_details", None)
    return Reply(
        # Keep only visible text blocks; thinking blocks are counted, not kept.
        text="".join(block.text for block in resp.content if getattr(block, "type", None) == "text"),
        served_model=getattr(resp, "model", None),
        stop_reason=getattr(resp, "stop_reason", None),
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        thinking_blocks=sum(t in ("thinking", "redacted_thinking") for t in types),
        refusal_category=getattr(stop_details, "category", None),
    )


def call_openai(model: str, prompt: str, temperature: float | None, max_tokens: int) -> Reply:
    import openai

    client = openai.OpenAI(max_retries=0)  # reads OPENAI_API_KEY
    kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_completion_tokens": max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    try:
        resp = client.chat.completions.create(**kwargs)
    except openai.BadRequestError as exc:
        if temperature is not None and _looks_like_temperature_error(exc):
            raise TemperatureUnsupported(str(exc)) from exc
        raise
    choice = resp.choices[0]
    usage = getattr(resp, "usage", None)
    return Reply(
        text=choice.message.content or "",
        served_model=getattr(resp, "model", None),
        stop_reason=getattr(choice, "finish_reason", None),
        input_tokens=getattr(usage, "prompt_tokens", None),
        output_tokens=getattr(usage, "completion_tokens", None),
    )


def call_google(model: str, prompt: str, temperature: float | None, max_tokens: int) -> Reply:
    from google import genai
    from google.genai import types

    client = genai.Client()  # reads GEMINI_API_KEY or GOOGLE_API_KEY
    config = types.GenerateContentConfig(max_output_tokens=max_tokens)
    if temperature is not None:
        config.temperature = temperature
    try:
        resp = client.models.generate_content(model=model, contents=prompt, config=config)
    except Exception as exc:  # the google SDK raises a generic ClientError
        if temperature is not None and _looks_like_temperature_error(exc):
            raise TemperatureUnsupported(str(exc)) from exc
        raise
    finish = resp.candidates[0].finish_reason if resp.candidates else None
    usage = getattr(resp, "usage_metadata", None)
    return Reply(
        text=resp.text or "",
        served_model=getattr(resp, "model_version", None),
        stop_reason=getattr(finish, "value", finish),
        input_tokens=getattr(usage, "prompt_token_count", None),
        output_tokens=getattr(usage, "candidates_token_count", None),
    )


def call_mock(model: str, prompt: str, temperature: float | None, max_tokens: int) -> Reply:
    """Offline stand in for testing the pipeline. Its numbers mean nothing."""
    base = {"fried": 15, "bacon": 10, "fish and chips": 15, "steamed vegetables": 90, "oatmeal": 90, "skinless": 90}
    centre = next((v for k, v in base.items() if k in prompt), 50)
    spread = 0 if temperature == 0 else (4 if centre != 50 else 13)
    seed = int(hashlib.sha256(f"{prompt}{random.random()}".encode()).hexdigest(), 16)
    score = round(random.Random(seed).gauss(centre, spread))
    score = max(0, min(100, score))
    return Reply(
        text=f"Mock reasoning for testing only.\nScore: {score}",
        served_model=model,
        stop_reason="end_turn",
        input_tokens=len(prompt) // 4,
        output_tokens=12,
    )


PROVIDERS = {
    "anthropic": (call_anthropic, "ANTHROPIC_API_KEY"),
    "openai": (call_openai, "OPENAI_API_KEY"),
    "google": (call_google, None),
    "mock": (call_mock, None),
}


def has_credentials(provider: str) -> bool:
    if provider == "mock":
        return True
    if provider == "google":
        return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return bool(os.environ.get(PROVIDERS[provider][1]))
