"""
providers/anthropic.py
======================
Anthropic Claude via the native Messages API. The system prompt is a top-level
field (not a message), and token usage is under ``usage.{input,output}_tokens``.
"""
from __future__ import annotations

from typing import Optional

from base import BaseProvider, RawCompletion
from config import DecodingConfig
from schema import TokenUsage

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def generate(self, prompt: str, decoding: DecodingConfig,
                 system_prompt: Optional[str] = None) -> RawCompletion:
        requests = self._require_requests()
        payload: dict = {
            "model": self.model,
            "max_tokens": decoding.max_tokens,
            "temperature": decoding.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if decoding.top_p is not None:
            payload["top_p"] = decoding.top_p
        if system_prompt:
            payload["system"] = system_prompt

        resp = requests.post(
            self.base_url or _API_URL,
            headers={"x-api-key": self._api_key,
                     "anthropic-version": _API_VERSION,
                     "content-type": "application/json"},
            json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        usage = data.get("usage", {}) or {}
        return RawCompletion(
            text=text,
            resolved_model=data.get("model"),
            finish_reason=data.get("stop_reason"),
            request_id=data.get("id") or resp.headers.get("request-id"),
            usage=TokenUsage(
                prompt_tokens=usage.get("input_tokens"),
                completion_tokens=usage.get("output_tokens"),
                total_tokens=(usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                              if usage else None)),
            raw=data)
