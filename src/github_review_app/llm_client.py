"""OpenAI 互換 API を使ったレビュー生成."""

from __future__ import annotations

import json
import sys
from typing import Any

import openai
from openai import OpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from .config import LLMConfig


class ReviewError(RuntimeError):
    """レビュー生成の失敗."""


class ReviewClient:
    """chat completions API に diff のレビューを依頼する."""

    def __init__(
        self, config: LLMConfig, *, client: OpenAI | None = None
    ) -> None:
        self._config = config
        self._client = client or OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
        )

    def review(self, diff: str, *, debug: bool = False) -> str:
        """diff を LLM に渡し、日本語のレビューコメントを返す."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._config.system_prompt},
            {"role": "user", "content": f"```diff\n{diff}\n```"},
        ]
        if debug:
            self._debug(
                json.dumps(
                    {"model": self._config.model, "messages": messages},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        try:
            completion = self._client.chat.completions.create(
                model=self._config.model,
                messages=messages,
            )
        except openai.OpenAIError as exc:
            raise ReviewError(f"review request failed: {exc}") from exc
        if debug:
            self._debug(completion.model_dump_json(indent=2))
        return _extract_review_text(completion)

    def _debug(self, message: str) -> None:
        endpoint = f"{self._config.base_url}/chat/completions"
        print(f"[debug] POST {endpoint}\n{message}", file=sys.stderr)


def _extract_review_text(completion: ChatCompletion) -> str:
    if not completion.choices:
        raise ReviewError("the chat completion response has no choices")
    message = completion.choices[0].message

    text = _coerce_content(message.content)
    if text:
        return text

    # reasoning モデル向けのフォールバック
    extra = getattr(message, "model_extra", None) or {}
    for key in ("reasoning_content", "reasoning"):
        fallback = extra.get(key)
        if isinstance(fallback, str) and fallback.strip():
            return fallback
    raise ReviewError("the chat completion response has no assistant text")


def _coerce_content(content: Any) -> str | None:
    if isinstance(content, str):
        return content if content.strip() else None
    if isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        ]
        return "".join(parts) or None
    return None
