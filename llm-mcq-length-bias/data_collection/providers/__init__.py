"""
providers package — registry + factory.

Adding a provider = drop a module here and register its class below. The run loop
depends only on ``BaseProvider`` (open/closed principle).
"""
from __future__ import annotations

from typing import Type

from base import BaseProvider
from config import ProviderConfig
from providers.anthropic import AnthropicProvider
from providers.google import GoogleProvider
from providers.meta import MetaProvider
from providers.mistral import MistralProvider
from providers.openai import OpenAIProvider

REGISTRY: dict[str, Type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "meta": MetaProvider,
    "mistral": MistralProvider,
}


def get_provider(cfg: ProviderConfig, api_key: str,
                 timeout_s: float = 120.0) -> BaseProvider:
    """Instantiate the provider named in ``cfg`` (fails loudly on unknown names)."""
    try:
        cls = REGISTRY[cfg.name]
    except KeyError as e:
        raise ValueError(f"unknown provider '{cfg.name}'; "
                         f"available: {sorted(REGISTRY)}") from e
    return cls(model=cfg.model, api_key=api_key,
               base_url=cfg.base_url, timeout_s=timeout_s)
