"""
providers/openai.py
===================
OpenAI Chat Completions provider, and the reusable ``OpenAICompatibleProvider``
base that Meta (Llama) and Mistral subclass — they all speak the same
``/chat/completions`` schema, differing only in ``base_url`` and key. (DRY.)
"""
from __future__ import annotations

from typing import Optional

from base import BaseProvider, RawCompletion
from config import DecodingConfig
from schema import TokenUsage


class OpenAICompatibleProvider(BaseProvider):
    """Any vendor exposing the OpenAI ``/chat/completions`` contract."""

    name = "openai-compatible"
    default_base_url = "https://api.openai.com/v1"

    def generate(self, prompt: str, decoding: DecodingConfig,
                 system_prompt: Optional[str] = None) -> RawCompletion:
        requests = self._require_requests()
        url = (self.base_url or self.default_base_url).rstrip("/") + "/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": decoding.temperature,
            "max_tokens": decoding.max_tokens,
        }
        if decoding.top_p is not None:
            payload["top_p"] = decoding.top_p
        if decoding.seed is not None:
            payload["seed"] = decoding.seed

        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {self._api_key}",
                     "Content-Type": "application/json"},
            json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {}) or {}
        return RawCompletion(
            text=choice["message"]["content"],
            resolved_model=data.get("model"),
            finish_reason=choice.get("finish_reason"),
            request_id=data.get("id") or resp.headers.get("x-request-id"),
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens")),
            raw=data)


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"
