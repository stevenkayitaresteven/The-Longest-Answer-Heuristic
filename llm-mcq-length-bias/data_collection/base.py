"""
base.py
=======
The provider interface (SOLID: clients depend on this abstraction, not on any
concrete SDK). A provider turns a prompt + decoding parameters into a
``RawCompletion`` carrying the text *and* the provenance the schema needs.

Concrete providers live in ``providers/``. Network I/O uses ``requests`` and is
lazy-imported so unit tests (which inject a fake provider) need no network stack.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Optional

from config import DecodingConfig
from schema import TokenUsage


@dataclass
class RawCompletion:
    """Everything a provider returns, normalised across vendors."""
    text: str
    resolved_model: Optional[str]
    finish_reason: Optional[str]
    request_id: Optional[str]
    usage: TokenUsage
    raw: dict = field(default_factory=dict)


class BaseProvider(abc.ABC):
    """Abstract provider. Subclasses implement :meth:`generate` only."""

    #: registry name, set by subclasses
    name: str = "base"

    def __init__(self, model: str, api_key: str,
                 base_url: Optional[str] = None, timeout_s: float = 120.0):
        self.model = model
        self._api_key = api_key
        self.base_url = base_url
        self.timeout_s = timeout_s

    @abc.abstractmethod
    def generate(self, prompt: str, decoding: DecodingConfig,
                 system_prompt: Optional[str] = None) -> RawCompletion:
        """Perform one completion request and return a normalised result.

        Implementations must raise on HTTP/transport errors (so the retry layer
        can act); they must not swallow errors or return partial text silently.
        """
        raise NotImplementedError

    @staticmethod
    def _require_requests():
        try:
            import requests
            return requests
        except ImportError as e:  # explicit
            raise RuntimeError("the live collection path needs `requests` "
                               "(pip install requests)") from e
