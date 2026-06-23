"""Unit tests for provenance records and traceability."""
import json

from schema import GenerationCall, MCQRecord, TokenUsage, stable_hash, new_id


def _make_call():
    return GenerationCall(
        call_id=new_id("call"), provider="openai", model="gpt-x",
        resolved_model="gpt-x-2026", timestamp_utc="2026-06-23T00:00:00Z",
        temperature=0.7, top_p=1.0, seed=7, max_tokens=4000,
        system_prompt=None, prompt="P", raw_response="R", finish_reason="stop",
        request_id="req-1", latency_s=0.5, usage=TokenUsage(10, 20, 30),
        subject="biology", difficulty="hard", n_requested=3, k_options=4,
        harness_version="1.0.0", config_hash="abc123")


def test_stable_hash_is_deterministic_and_order_independent():
    assert stable_hash({"a": 1, "b": 2}) == stable_hash({"b": 2, "a": 1})
    assert stable_hash({"a": 1}) != stable_hash({"a": 2})


def test_record_is_traceable_to_call():
    call = _make_call()
    parsed = {"stem": "Q", "options": ["a", "b", "c", "d"], "answer_index": 1}
    rec = MCQRecord.from_parsed(parsed, call=call, parse_index=2,
                                collected_at_utc="2026-06-23T00:00:01Z")
    assert rec.source_call_id == call.call_id      # foreign key present
    assert rec.parse_index == 2
    assert rec.provider == "openai" and rec.subject == "biology"
    assert rec.k == 4 and rec.answer_index == 1
    assert "openai/gpt-x/biology/hard/0002" == rec.id


def test_record_roundtrips_json_and_is_analysis_ready():
    call = _make_call()
    parsed = {"stem": "Q", "options": ["a", "b", "c", "d"], "answer_index": 0}
    rec = MCQRecord.from_parsed(parsed, call=call, parse_index=0,
                                collected_at_utc="2026-06-23T00:00:01Z")
    d = json.loads(rec.to_json())
    # the keys metrics.py relies on must be present
    for key in ("options", "answer_index", "model", "subject", "difficulty"):
        assert key in d


def test_call_json_contains_full_provenance():
    d = json.loads(_make_call().to_json())
    for key in ("provider", "model", "resolved_model", "temperature", "seed",
                "prompt", "raw_response", "usage", "config_hash",
                "harness_version", "timestamp_utc"):
        assert key in d
    assert d["usage"]["total_tokens"] == 30
