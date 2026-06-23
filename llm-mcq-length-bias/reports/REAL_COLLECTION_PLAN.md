# REAL_COLLECTION_PLAN.md — Phase 6: Breaking the Synthetic Loop

## Goal

Replace the synthetic corpus with **real model outputs**, collected through a
modular, reproducible, auditable harness. This is the only way to earn the
empirical claims the synthetic study cannot support (audit blockers B1/B4). The
code is implemented in `data_collection/`; this document is the plan and the
operating protocol.

## Why a new package (not just `src/collect.py`)

`src/collect.py` works but is a single file: it records minimal provenance (no
resolved model version, token counts, latency, request id, or config hash), is not
configuration-driven (CLI flags only), has a fixed `time.sleep(1)` rather than a
real retry policy, prints rather than logs, and has no experiment tracking or
tests. `data_collection/` keeps its good ideas (length-neutral prompt, balanced
grid, defensive parsing, OpenAI-compatible adapter) and adds everything required
for a *publishable* collection.

## Architecture (modular, SOLID, DRY)

```
config.py  ─►  run.py  ─►  providers/<name>.py ─►  (live API)
   │             │                 ▲
   │             │                 └── base.BaseProvider  (interface; OCP)
   │             ▼
   │        schema.GenerationCall  +  schema.MCQRecord   (provenance + traceability)
   │             │
   ├─ retry.py (backoff)   ├─ parsing.py (defensive)   ├─ logging_setup.py (JSON)
   └────────────────────────────────  tracking.py (jsonl|mlflow|none)
```

- **Separation of concerns:** config, transport (providers), provenance (schema),
  reliability (retry), parsing, logging, and tracking are independent modules.
- **Open/closed:** adding a provider = new module + one registry line; the run loop
  depends only on `BaseProvider`.
- **DRY:** OpenAI, Meta (Llama), and Mistral share one `OpenAICompatibleProvider`;
  Anthropic and Google have native adapters.

## Requirement-by-requirement

### Reproducibility — *every call stores:*
model name, **resolved** model/version (what the provider says it served),
UTC timestamp, temperature/top_p/seed, the full prompt, the raw response, and
prompt/completion/total token counts — plus a `config_hash` fingerprinting the
exact settings and a `harness_version`. (`schema.GenerationCall`.)

### Traceability
Each `MCQRecord` carries `source_call_id` (→ `GenerationCall.call_id`) and a
`parse_index`, so any MCQ is traceable to the request/response that produced it and
its position within that response. Verified by `tests/test_schema.py` and the
end-to-end `tests/test_run_dryrun.py`.

### Configuration driven
All experimental parameters (grid, decoding, retry policy, providers, tracking,
pauses) live in a YAML/TOML/JSON file (`config.py`; examples in `configs/`).
**API keys are never in config** — only the *name* of the env var holding each key
(`resolve_api_key` fails loudly if unset). No magic numbers or hard-coded paths in
the run logic.

### Rate-limit safety
`retry.call_with_retry` implements exponential backoff with jitter and a delay cap,
retries only transient errors (network/timeout, HTTP 408/429/5xx) and **never**
auth errors (401/403), and raises `RetryError` on exhaustion. A permanently failed
cell is logged and recorded in `manifest.json` — never silently skipped. Verified
by `tests/test_retry.py` (including the capped backoff schedule 1,2,4,4).

### Logging
`logging_setup.py` emits structured JSON-lines (one object per event, with `run_id`
bound) to stderr and to `outputs/<run_id>/run.log`.

### Experiment tracking — **recommendation: MLflow**
`tracking.py` provides one interface with three backends: `jsonl` (default, zero
dependencies, fully offline), `mlflow`, and `none`.

> **We recommend MLflow** for the real study. It is open-source, runs entirely
> locally against a file store (`file:./mlruns`) with no account or network
> dependency, logs params/metrics/artifacts and diffs runs out of the box, and
> coexists with the JSONL provenance we already write. **Weights & Biases** is
> excellent but cloud-first (account + outbound network), which is friction for a
> reproducible, possibly air-gapped audit. **Sacred** is lighter but less actively
> maintained and needs a separate store (e.g. MongoDB) for its strengths. For an
> offline-capable, audit-friendly harness, MLflow is the best fit; the
> dependency-free `jsonl` backend is the default so the pipeline runs anywhere.

## Operating protocol for the real run (preregisterable)

1. **Fix the design** in a committed config: 5 subjects × 3 difficulties,
   `n_per_cell` chosen for a target CI half-width on `E` (the bootstrap machinery
   exists; see `STATISTICAL_VALIDITY_REPORT.md` for the clustering-aware variance),
   `k=4`, temperature and seed logged.
2. **Pin model ids** to specific versions on the run date (they drift); the
   resolved version is captured per call regardless.
3. **Smoke test** offline: `python run.py --config <cfg> --dry-run`.
4. **Collect** per provider (set the key env vars first). One run writes
   `corpus.jsonl` + `calls.jsonl` + `manifest.json` under `outputs/<run_id>/`.
5. **Analyze** with the *existing* pipeline and the *clustering-aware* statistics:
   `python ../src/analyze.py --data outputs/<run_id>/corpus.jsonl --tag real`.
   (Confirmed compatible — a dry-run corpus feeds `analyze.py` unchanged.)
6. **Release** the corpus subject to each provider's terms of service; release the
   `manifest.json` + `calls.jsonl` provenance for full auditability.

## Honest status

- The harness is implemented, unit-tested (18 tests pass), and demonstrated
  end-to-end with an **offline FakeProvider** (clearly labelled `resolved_model =
  "FAKE"` in provenance). **No real API has been called.**
- The `FakeProvider` exists only to exercise plumbing and tests; it is never a data
  source and cannot be mistaken for one (its provenance says so).
- Running step 4 against live endpoints requires the user's own credentials and ToS
  compliance and is the one step this environment cannot perform.

## Files added

`data_collection/` — `schema.py`, `config.py`, `retry.py`, `parsing.py`,
`logging_setup.py`, `tracking.py`, `base.py`, `run.py`,
`providers/{__init__,openai,anthropic,google,meta,mistral}.py`,
`prompts/mcq_generation.txt`, `configs/example.{toml,yaml}`, `requirements.txt`,
`conftest.py`, `README.md`, and `tests/test_{parsing,retry,schema,run_dryrun}.py`.
