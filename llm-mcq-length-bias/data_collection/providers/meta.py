"""
providers/meta.py
=================
Meta Llama models. Llama is most commonly served through an OpenAI-compatible
gateway (Meta's own Llama API, or Together / Fireworks / Groq). Set ``base_url``
in the config to point at your chosen gateway and ``api_key_env`` to its key var;
the default below targets Meta's OpenAI-compatible endpoint.
"""
from __future__ import annotations

from providers.openai import OpenAICompatibleProvider


class MetaProvider(OpenAICompatibleProvider):
    name = "meta"
    default_base_url = "https://api.llama.com/compat/v1"
