"""
schema.py
=========
Provenance-complete data structures for the real MCQ-collection pipeline.

Two record types, written to two JSONL streams so that *every generated MCQ is
fully traceable back to the exact API call that produced it*:

  * ``GenerationCall`` -- one row per provider API call. Captures everything needed
    to reproduce or audit the call: provider, model id, *resolved* model version,
    decoding parameters, the full prompt, the raw response, token counts, latency,
    request id, and the hash of the configuration that drove the run.
  * ``MCQRecord``      -- one row per parsed multiple-choice item, in the schema
    consumed by ``src/metrics.py`` / ``src/analyze.py``. Each record carries a
    ``source_call_id`` foreign key into the ``GenerationCall`` stream and a
    ``parse_index`` so the item can be located within that call's response.

Design notes
------------
* Dataclasses (not a heavy validation library) keep the dependency surface tiny;
  ``to_json``/``from_json`` give stable serialisation.
* No field is optional-by-omission: missing provenance is recorded explicitly as
  ``None`` so an audit can distinguish "unknown" from "not captured".
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Optional


def new_id(prefix: str) -> str:
    """A short, collision-resistant id with a human-readable prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def stable_hash(obj: Any) -> str:
    """Deterministic SHA-256 (first 16 hex chars) of any JSON-serialisable object.
    Used to fingerprint a run configuration for reproducibility."""
    blob = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


@dataclass
class TokenUsage:
    """Token accounting as reported by the provider (None where not reported)."""
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


@dataclass
class GenerationCall:
    """Full provenance for a single provider API call."""
    call_id: str
    provider: str
    model: str                      # the id we requested
    resolved_model: Optional[str]   # the id/version the provider says it served
    timestamp_utc: str              # ISO-8601, UTC
    temperature: float
    top_p: Optional[float]
    seed: Optional[int]
    max_tokens: int
    system_prompt: Optional[str]
    prompt: str
    raw_response: str
    finish_reason: Optional[str]
    request_id: Optional[str]       # provider-side request id, if any
    latency_s: float
    usage: TokenUsage
    # experimental-cell context (the balanced grid coordinates)
    subject: Optional[str] = None
    difficulty: Optional[str] = None
    n_requested: Optional[int] = None
    k_options: Optional[int] = None
    # reproducibility anchors
    harness_version: str = ""
    config_hash: str = ""
    extra: dict = field(default_factory=dict)

    def to_json(self) -> str:
        d = asdict(self)
        return json.dumps(d, ensure_ascii=False)


@dataclass
class MCQRecord:
    """One multiple-choice item, traceable to its generating call."""
    id: str
    stem: str
    options: list[str]
    answer_index: int
    # cell context (mirrors the synthetic schema so analyze.py is reusable)
    model: str
    provider: str
    subject: str
    difficulty: str
    temperature: float
    k: int
    # traceability
    source_call_id: str
    parse_index: int                # position of this item within the call response
    collected_at_utc: str
    extra: dict = field(default_factory=dict)

    def to_analysis_dict(self) -> dict:
        """The subset/shape expected by ``src/metrics.py`` (plus provenance keys,
        which the metrics ignore but which keep the corpus self-describing)."""
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @staticmethod
    def from_parsed(parsed: dict, *, call: "GenerationCall", parse_index: int,
                    collected_at_utc: str) -> "MCQRecord":
        """Build a fully-populated, traceable record from a parsed item dict and
        its originating call."""
        item_id = (f"{call.provider}/{call.model}/{call.subject}/"
                   f"{call.difficulty}/{parse_index:04d}")
        return MCQRecord(
            id=item_id,
            stem=str(parsed.get("stem", "")).strip(),
            options=[str(o).strip() for o in parsed["options"]],
            answer_index=int(parsed["answer_index"]),
            model=call.model,
            provider=call.provider,
            subject=call.subject or "NA",
            difficulty=call.difficulty or "NA",
            temperature=call.temperature,
            k=call.k_options or len(parsed["options"]),
            source_call_id=call.call_id,
            parse_index=parse_index,
            collected_at_utc=collected_at_utc,
        )
