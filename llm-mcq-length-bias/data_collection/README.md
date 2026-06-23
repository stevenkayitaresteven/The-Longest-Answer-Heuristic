# `data_collection/` — real cross-model MCQ collection

A modular, reproducible, provider-agnostic harness for collecting the **real**
MCQ corpus that breaks the synthetic loop. It supersedes the single-file
`src/collect.py` with a package that records full provenance, is configuration-
driven, is rate-limit safe, logs structured events, and integrates experiment
tracking. The corpus it writes is directly consumable by `src/analyze.py`.

## Layout

```
data_collection/
  schema.py          GenerationCall + MCQRecord (full provenance, traceability)
  config.py          typed config; loads YAML/TOML/JSON; keys come from env vars
  retry.py           exponential-backoff retry (rate-limit safety, no silent fails)
  parsing.py         defensive JSON→MCQ extraction (counts rejects)
  logging_setup.py   structured JSON-lines logging
  tracking.py        ExperimentTracker: jsonl (default) | mlflow | none
  base.py            BaseProvider interface (+ RawCompletion)
  providers/         openai · anthropic · google · meta · mistral  (+ registry)
  run.py             config-driven driver (+ offline FakeProvider for --dry-run)
  prompts/           length-neutral generation prompt
  configs/           example.toml / example.yaml (no secrets)
  tests/             pytest unit + end-to-end dry-run tests
  outputs/           run artifacts (gitignored): corpus.jsonl, calls.jsonl, manifest.json
```

## Quick start

```bash
pip install -r requirements.txt          # only `requests` is required for live runs

# 1) offline smoke test — no keys, no network:
python run.py --config configs/example.toml --dry-run

# 2) real run — set the key env vars named in the config, then:
export OPENAI_API_KEY=...                 # ANTHROPIC_API_KEY / GOOGLE_API_KEY / ...
python run.py --config configs/example.toml                 # all enabled providers
python run.py --config configs/example.toml --provider openai   # just one

# 3) analyze the collected corpus with the existing pipeline:
python ../src/analyze.py --data outputs/<run_id>/corpus.jsonl --tag real \
       --figdir ../figures --outdir ../results
```

## What every run records (under `outputs/<run_id>/`)

| File | Contents |
|------|----------|
| `corpus.jsonl` | one `MCQRecord` per item (analysis-ready; carries `source_call_id`) |
| `calls.jsonl`  | one `GenerationCall` per API call: model, **resolved** version, timestamp, temperature/top_p/seed, full prompt + raw response, token counts, request id, latency, `config_hash` |
| `manifest.json`| config snapshot + hash, environment, per-cell yields, and **failures** (nothing is dropped silently) |
| `run.log`      | structured JSON logs |
| `tracking.jsonl` | params/metrics (or MLflow if configured) |

Every `MCQRecord.source_call_id` resolves to a `GenerationCall.call_id`, so any
item is traceable to the exact request/response that produced it.

## Run the tests

```bash
cd data_collection && python -m pytest -q
```
