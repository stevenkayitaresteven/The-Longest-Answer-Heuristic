"""End-to-end test of the collection driver using the offline FakeProvider.

Verifies that a dry run produces a traceable corpus, a provenance call log, and a
complete manifest — with no network and no API keys."""
import json
from pathlib import Path

import run as run_module


def _write_config(tmp_path: Path) -> Path:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "mcq_generation.txt").write_text(
        "Produce exactly {n} multiple-choice questions on {subject} at "
        "{difficulty} difficulty with {k} options each. Return JSON.\n")
    cfg = {
        "output_dir": str(tmp_path / "outputs"),
        "prompt_path": "prompts/mcq_generation.txt",
        "request_pause_s": 0.0,
        "grid": {"subjects": ["biology", "history"],
                 "difficulties": ["easy", "hard"],
                 "n_per_cell": 3, "k_options": 4},
        "decoding": {"temperature": 0.5, "max_tokens": 1000},
        "retry": {"max_retries": 2, "base_delay_s": 0.0, "max_delay_s": 0.0},
        "tracking": {"backend": "jsonl", "experiment_name": "test"},
        "providers": [{"name": "openai", "model": "fake-model",
                       "api_key_env": "UNUSED_IN_DRY_RUN", "enabled": True}],
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(cfg))
    return p


def test_dry_run_produces_traceable_corpus(tmp_path):
    cfg_path = _write_config(tmp_path)
    manifest = run_module.main(["--config", str(cfg_path), "--dry-run"])

    run_dir = Path(manifest["config"]["output_dir"]) / manifest["run_id"]
    corpus = [json.loads(l) for l in (run_dir / "corpus.jsonl").read_text().splitlines()]
    calls = [json.loads(l) for l in (run_dir / "calls.jsonl").read_text().splitlines()]

    # 2 subjects x 2 difficulties x 3 items = 12 items, 4 calls
    assert len(corpus) == 12
    assert len(calls) == 4
    assert manifest["totals"]["items"] == 12
    assert manifest["totals"]["failed_cells"] == 0

    # every corpus item is traceable to a logged call
    call_ids = {c["call_id"] for c in calls}
    assert all(item["source_call_id"] in call_ids for item in corpus)

    # provenance is recorded (fake runs are clearly labelled)
    assert all(c["resolved_model"] == "FAKE" for c in calls)
    assert all(c["config_hash"] == manifest["config_hash"] for c in calls)

    # manifest + provenance files all written
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "tracking.jsonl").exists()
    assert (run_dir / "run.log").exists()
