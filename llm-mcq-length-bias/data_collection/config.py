"""
config.py
=========
Configuration-driven setup for the collection pipeline. No experimental parameter
is hard-coded in the run logic; everything below is read from a YAML, TOML, or JSON
file (auto-detected by extension). API keys are *never* stored in config files —
only the *name* of the environment variable that holds each key.

The config is hashed (``schema.stable_hash``) and the hash is stamped onto every
``GenerationCall`` so a corpus can be tied back to the exact settings that produced
it.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class GridConfig:
    """The balanced experimental design: every (subject x difficulty) cell gets
    ``n_per_cell`` items with ``k_options`` options each."""
    subjects: list[str]
    difficulties: list[str]
    n_per_cell: int
    k_options: int


@dataclass
class DecodingConfig:
    """Decoding parameters logged with every call for reproducibility."""
    temperature: float = 0.7
    top_p: Optional[float] = None
    seed: Optional[int] = None
    max_tokens: int = 4000


@dataclass
class RetryConfig:
    """Exponential-backoff retry policy (no magic numbers in the call sites)."""
    max_retries: int = 5
    base_delay_s: float = 2.0
    max_delay_s: float = 60.0
    jitter: bool = True


@dataclass
class ProviderConfig:
    """One provider/model to collect from."""
    name: str                       # registry key: openai|anthropic|google|meta|mistral
    model: str                      # provider model id
    api_key_env: str                # NAME of the env var holding the key
    base_url: Optional[str] = None  # override for OpenAI-compatible providers
    enabled: bool = True


@dataclass
class TrackingConfig:
    backend: str = "jsonl"          # jsonl | mlflow | none
    experiment_name: str = "mcq-length-bias-collection"
    uri: Optional[str] = None       # e.g. mlflow file:./mlruns


@dataclass
class CollectionConfig:
    grid: GridConfig
    decoding: DecodingConfig
    retry: RetryConfig
    providers: list[ProviderConfig]
    tracking: TrackingConfig
    prompt_path: str = "prompts/mcq_generation.txt"
    output_dir: str = "outputs"
    request_pause_s: float = 1.0    # politeness pause between successful calls

    def config_hash(self) -> str:
        from schema import stable_hash
        return stable_hash(asdict(self))

    def enabled_providers(self) -> list[ProviderConfig]:
        return [p for p in self.providers if p.enabled]


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def _read_raw(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"config not found: {p}")
    suffix = p.suffix.lower()
    text = p.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(text)
    if suffix == ".toml":
        import tomllib  # stdlib in Python 3.11+
        return tomllib.loads(text)
    if suffix in (".yaml", ".yml"):
        try:
            import yaml
        except ImportError as e:  # explicit, never silent
            raise RuntimeError(
                "YAML config requires PyYAML (`pip install pyyaml`), or use "
                ".toml/.json instead.") from e
        return yaml.safe_load(text)
    raise ValueError(f"unsupported config extension: {suffix} (use .yaml/.toml/.json)")


def load_config(path: str | Path) -> CollectionConfig:
    """Parse a config file into a typed ``CollectionConfig`` (fails loudly on any
    missing required key)."""
    raw = _read_raw(path)
    grid = GridConfig(**raw["grid"])
    decoding = DecodingConfig(**raw.get("decoding", {}))
    retry = RetryConfig(**raw.get("retry", {}))
    providers = [ProviderConfig(**p) for p in raw["providers"]]
    tracking = TrackingConfig(**raw.get("tracking", {}))
    top = {k: v for k, v in raw.items()
           if k in {"prompt_path", "output_dir", "request_pause_s"}}
    return CollectionConfig(grid=grid, decoding=decoding, retry=retry,
                            providers=providers, tracking=tracking, **top)


def resolve_api_key(provider: ProviderConfig) -> str:
    """Fetch the key from the named env var; raise (never proceed silently) if absent."""
    key = os.environ.get(provider.api_key_env)
    if not key:
        raise EnvironmentError(
            f"provider '{provider.name}' needs env var {provider.api_key_env} "
            f"to be set (it holds the API key; keys are never stored in config).")
    return key
