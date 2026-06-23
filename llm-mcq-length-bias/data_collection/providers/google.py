"""
providers/google.py
===================
Google Gemini via the ``generateContent`` REST endpoint. The system prompt maps
to ``system_instruction``; decoding params go under ``generationConfig``; token
usage is under ``usageMetadata``.
"""
from __future__ import annotations

from typing import Optional

from base import BaseProvider, RawCompletion
from config import DecodingConfig
from schema import TokenUsage

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GoogleProvider(BaseProvider):
    name = "google"

    def generate(self, prompt: str, decoding: DecodingConfig,
                 system_prompt: Optional[str] = None) -> RawCompletion:
        requests = self._require_requests()
        base = (self.base_url or _BASE).rstrip("/")
        url = f"{base}/{self.model}:generateContent?key={self._api_key}"

        gen_config: dict = {
            "temperature": decoding.temperature,
            "maxOutputTokens": decoding.max_tokens,
        }
        if decoding.top_p is not None:
            gen_config["topP"] = decoding.top_p

        payload: dict = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_config,
        }
        if system_prompt:
            payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        resp = requests.post(url, headers={"Content-Type": "application/json"},
                             json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        cand = (data.get("candidates") or [{}])[0]
        parts = cand.get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        usage = data.get("usageMetadata", {}) or {}
        return RawCompletion(
            text=text,
            resolved_model=data.get("modelVersion") or self.model,
            finish_reason=cand.get("finishReason"),
            request_id=resp.headers.get("x-request-id"),
            usage=TokenUsage(
                prompt_tokens=usage.get("promptTokenCount"),
                completion_tokens=usage.get("candidatesTokenCount"),
                total_tokens=usage.get("totalTokenCount")),
            raw=data)
