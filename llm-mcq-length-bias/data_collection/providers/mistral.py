"""
providers/mistral.py
====================
Mistral AI. Mistral's ``/v1/chat/completions`` endpoint is OpenAI-compatible, so
we reuse the shared base and only change the default base URL.
"""
from __future__ import annotations

from providers.openai import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"
    default_base_url = "https://api.mistral.ai/v1"
