from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from ..agent_research import DEFAULT_FAST_MODEL, resolve_openai_key
from ..models import CandidateConfig, CandidateResponse, TokenCounts
from .base import CandidateAdapter, CandidateAdapterError

_MAX_SYSTEM_PROMPT_CHARS = 20000


class PromptAgentAdapter(CandidateAdapter):
    """Executes a user-supplied agent definition (an ``agent.md`` / ``AGENTS.md``)
    as the candidate under test via OpenAI's ``responses.create``.

    The agent's own markdown drives behaviour: it is sent as the developer/system
    message so the agent's persona, operating principles, and tools take
    precedence over the generic HR-screening preamble Interviu adds to every
    ``context``. The endpoint that constructs this adapter only does so in live
    mode (an OpenAI key is present); with no key it falls back to the deterministic
    mock, so this adapter raises if it cannot resolve a key.
    """

    def __init__(self, config: CandidateConfig):
        self.config = config
        system_prompt = (config.system_prompt or "").strip()
        if not system_prompt:
            raise CandidateAdapterError(
                "openai-compatible candidate requires a system_prompt (the agent.md definition)."
            )
        # Defensive size cap before the markdown reaches an LLM call.
        self.system_prompt = system_prompt[:_MAX_SYSTEM_PROMPT_CHARS]
        self.model = config.model or DEFAULT_FAST_MODEL

    async def ask(self, context: str, question: str) -> CandidateResponse:
        key = resolve_openai_key()
        if not key:
            raise CandidateAdapterError(
                "No OpenAI key found. Add OPENAI_API_KEY (or openai_key) to the project env "
                "file or the API process environment to run the agent in live mode."
            )

        started = time.perf_counter()
        # The agent's own definition is the developer message so its persona wins;
        # the generic Interviu preamble arrives only as user-supplied context that
        # the agent should interpret under its own rules.
        user_message = (
            "Interviu screening context (treat as task framing, your own agent "
            "definition above takes precedence):\n"
            f"{context}\n\n"
            f"Question:\n{question}"
        )
        response = await asyncio.to_thread(
            self._call_openai, key, user_message
        )
        latency_ms = max(1, int((time.perf_counter() - started) * 1000))

        text = _output_text(response)
        tokens = _token_counts(response, self.system_prompt, context, question, text)
        return CandidateResponse(
            answer=text,
            reasoning="",
            tool_calls=[],
            latency_ms=latency_ms,
            tokens=tokens,
        )

    def _call_openai(self, key: str, user_message: str) -> Any:
        from openai import OpenAI

        timeout_s = float(os.environ.get("INTERVIU_OPENAI_TIMEOUT_S", "90"))
        client = OpenAI(api_key=key, timeout=timeout_s)
        return client.responses.create(
            model=self.model,
            input=[
                {"role": "developer", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
        )


def _output_text(response: Any) -> str:
    """Extract reply text robustly across OpenAI SDK response shapes."""

    text = getattr(response, "output_text", None)
    if text:
        return text
    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            piece = getattr(content, "text", None)
            if piece:
                chunks.append(piece)
    return "".join(chunks)


def _token_counts(
    response: Any, system_prompt: str, context: str, question: str, answer: str
) -> TokenCounts:
    usage = getattr(response, "usage", None)
    if usage is not None:
        input_tokens = _usage_field(usage, "input_tokens")
        output_tokens = _usage_field(usage, "output_tokens")
        total_tokens = _usage_field(usage, "total_tokens")
        if input_tokens or output_tokens or total_tokens:
            if not total_tokens:
                total_tokens = input_tokens + output_tokens
            return TokenCounts(input=input_tokens, output=output_tokens, total=total_tokens)

    # No usage on the response: estimate ~4 chars per token.
    input_tokens = (len(system_prompt) + len(context) + len(question)) // 4
    output_tokens = len(answer) // 4
    return TokenCounts(
        input=input_tokens,
        output=output_tokens,
        total=input_tokens + output_tokens,
    )


def _usage_field(usage: Any, name: str) -> int:
    value = getattr(usage, name, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(name)
    try:
        return int(value) if value is not None else 0
    except (TypeError, ValueError):
        return 0
