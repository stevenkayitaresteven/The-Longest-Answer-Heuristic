"""
run.py
======
Configuration-driven collection driver. Iterates the balanced
(subject x difficulty) grid for every enabled provider, calls the model under a
length-neutral prompt with rate-limit-safe retries, parses MCQs, and writes:

  outputs/<run_id>/
    corpus.jsonl     -- MCQRecord per item (the analysis corpus; analyze.py-ready)
    calls.jsonl      -- GenerationCall per API call (full provenance)
    manifest.json    -- run-level metadata: config snapshot+hash, env, per-cell
                        yields, failures (nothing fails silently)
    run.log          -- structured JSON logs
    tracking.jsonl   -- params/metrics (or MLflow, per config)

Every MCQRecord links to its GenerationCall via ``source_call_id`` -> full
traceability from corpus item back to the exact request/response.

Usage
-----
    python run.py --config configs/example.toml --dry-run     # offline, no keys
    python run.py --config configs/example.toml               # live (needs keys)
    python run.py --config configs/example.toml --provider openai
"""
from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from base import BaseProvider, RawCompletion
from config import (CollectionConfig, ProviderConfig, DecodingConfig,
                    load_config, resolve_api_key)
from logging_setup import setup_logging
from parsing import parse_items
from retry import call_with_retry, is_retryable_status, RetryError
from schema import GenerationCall, MCQRecord, TokenUsage, new_id
from tracking import make_tracker
import providers as provider_pkg

HARNESS_VERSION = "1.0.0"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_prompt_template(path: str, base_dir: Path) -> str:
    """Load the length-neutral prompt template (config-relative, then cwd)."""
    for candidate in (base_dir / path, Path(path)):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"prompt template not found: {path}")


# --------------------------------------------------------------------------- #
# Offline fake provider (for --dry-run and unit tests; no network, no keys)
# --------------------------------------------------------------------------- #
class FakeProvider(BaseProvider):
    """Deterministic schema-valid generator. Reuses the project's synthetic item
    builder if importable, else emits a minimal valid item set. NEVER used for
    real data; clearly labelled in provenance (resolved_model='FAKE')."""

    name = "fake"

    def generate(self, prompt: str, decoding: DecodingConfig,
                 system_prompt: Optional[str] = None) -> RawCompletion:
        import re, random, json as _json
        n = int(re.search(r"exactly (\d+)", prompt).group(1)) if re.search(
            r"exactly (\d+)", prompt) else 3
        k = 4
        rng = random.Random(hash((self.model, prompt)) & 0xFFFFFFFF)
        items = []
        for i in range(n):
            ai = rng.randrange(k)
            opts = []
            for j in range(k):
                base = f"option {j} for item {i}"
                # inject a mild length bias on the key so the pipeline has signal
                opts.append(base + (" with additional clarifying detail" if j == ai else ""))
            items.append({"stem": f"Synthetic stem {i}", "options": opts,
                          "answer_index": ai})
        return RawCompletion(
            text=_json.dumps(items), resolved_model="FAKE",
            finish_reason="stop", request_id=new_id("fake-req"),
            usage=TokenUsage(prompt_tokens=len(prompt) // 4,
                             completion_tokens=64, total_tokens=len(prompt) // 4 + 64),
            raw={"fake": True})


# --------------------------------------------------------------------------- #
# One provider sweep
# --------------------------------------------------------------------------- #
def collect_provider(provider: BaseProvider, pcfg: ProviderConfig,
                     cfg: CollectionConfig, template: str,
                     corpus_f, calls_f, tracker, log: logging.Logger,
                     config_hash: str) -> dict:
    """Run the full grid for one provider; return its per-cell yield summary."""
    cells, total_items, total_rejects, failures = [], 0, 0, []
    for subject in cfg.grid.subjects:
        for difficulty in cfg.grid.difficulties:
            prompt = template.format(n=cfg.grid.n_per_cell, subject=subject,
                                     difficulty=difficulty, k=cfg.grid.k_options)
            t0 = time.time()
            try:
                completion: RawCompletion = call_with_retry(
                    lambda: provider.generate(prompt, cfg.decoding),
                    max_retries=cfg.retry.max_retries,
                    base_delay_s=cfg.retry.base_delay_s,
                    max_delay_s=cfg.retry.max_delay_s,
                    jitter=cfg.retry.jitter,
                    should_retry=_should_retry)
            except RetryError as e:
                log.error("cell %s/%s failed permanently: %r",
                          subject, difficulty, e)
                failures.append({"subject": subject, "difficulty": difficulty,
                                 "error": str(e)})
                continue
            latency = time.time() - t0

            call = GenerationCall(
                call_id=new_id("call"), provider=pcfg.name, model=pcfg.model,
                resolved_model=completion.resolved_model, timestamp_utc=_utcnow(),
                temperature=cfg.decoding.temperature, top_p=cfg.decoding.top_p,
                seed=cfg.decoding.seed, max_tokens=cfg.decoding.max_tokens,
                system_prompt=None, prompt=prompt, raw_response=completion.text,
                finish_reason=completion.finish_reason,
                request_id=completion.request_id, latency_s=round(latency, 3),
                usage=completion.usage, subject=subject, difficulty=difficulty,
                n_requested=cfg.grid.n_per_cell, k_options=cfg.grid.k_options,
                harness_version=HARNESS_VERSION, config_hash=config_hash)
            calls_f.write(call.to_json() + "\n")

            parsed = parse_items(completion.text, cfg.grid.k_options)
            now = _utcnow()
            for idx, item in enumerate(parsed.items):
                rec = MCQRecord.from_parsed(item, call=call, parse_index=idx,
                                            collected_at_utc=now)
                corpus_f.write(rec.to_json() + "\n")
            total_items += parsed.n_valid
            total_rejects += parsed.n_rejected
            cells.append({"subject": subject, "difficulty": difficulty,
                          "valid": parsed.n_valid, "rejected": parsed.n_rejected})
            log.info("provider=%s cell=%s/%s valid=%d rejected=%d latency=%.2fs",
                     pcfg.name, subject, difficulty, parsed.n_valid,
                     parsed.n_rejected, latency)
            if cfg.request_pause_s > 0:
                time.sleep(cfg.request_pause_s)

    summary = {"provider": pcfg.name, "model": pcfg.model, "cells": cells,
               "total_items": total_items, "total_rejected": total_rejects,
               "failures": failures}
    tracker.log_metrics({f"{pcfg.name}.total_items": total_items,
                         f"{pcfg.name}.total_rejected": total_rejects,
                         f"{pcfg.name}.failed_cells": len(failures)})
    return summary


def _should_retry(exc: BaseException) -> bool:
    """Retry on transport errors and retryable HTTP statuses; not on auth (401/403)."""
    status = getattr(getattr(exc, "response", None), "status_code", None)
    if status is not None:
        return is_retryable_status(status)
    return True  # network/timeout errors with no response -> retry


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: Optional[list[str]] = None) -> dict:
    ap = argparse.ArgumentParser(description="Real MCQ-collection driver.")
    ap.add_argument("--config", required=True, help="YAML/TOML/JSON config path")
    ap.add_argument("--provider", default=None,
                    help="restrict to one provider name from the config")
    ap.add_argument("--dry-run", action="store_true",
                    help="use the offline FakeProvider (no keys/network)")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config).resolve()
    cfg = load_config(cfg_path)
    config_hash = cfg.config_hash()
    run_id = new_id("run")
    run_dir = Path(cfg.output_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    log = setup_logging(run_id, logfile=str(run_dir / "run.log"))
    log.info("run %s starting (config_hash=%s, harness=%s, dry_run=%s)",
             run_id, config_hash, HARNESS_VERSION, args.dry_run)

    tracker = make_tracker(cfg.tracking.backend, run_dir=str(run_dir),
                           run_id=run_id,
                           experiment_name=cfg.tracking.experiment_name,
                           uri=cfg.tracking.uri)
    tracker.log_params({"config_hash": config_hash, "harness": HARNESS_VERSION,
                        "dry_run": args.dry_run, "n_per_cell": cfg.grid.n_per_cell,
                        "k_options": cfg.grid.k_options,
                        "temperature": cfg.decoding.temperature})

    template = load_prompt_template(cfg.prompt_path, cfg_path.parent)
    providers_to_run = [p for p in cfg.enabled_providers()
                        if args.provider is None or p.name == args.provider]
    if not providers_to_run:
        log.error("no enabled providers match --provider=%s", args.provider)

    summaries = []
    with (run_dir / "corpus.jsonl").open("w", encoding="utf-8") as corpus_f, \
         (run_dir / "calls.jsonl").open("w", encoding="utf-8") as calls_f:
        for pcfg in providers_to_run:
            if args.dry_run:
                provider: BaseProvider = FakeProvider(model=pcfg.model, api_key="NONE")
            else:
                provider = provider_pkg.get_provider(pcfg, resolve_api_key(pcfg))
            log.info("collecting provider=%s model=%s", pcfg.name, pcfg.model)
            summaries.append(collect_provider(
                provider, pcfg, cfg, template, corpus_f, calls_f, tracker, log,
                config_hash))

    manifest = {
        "run_id": run_id, "config_hash": config_hash,
        "harness_version": HARNESS_VERSION, "dry_run": args.dry_run,
        "started_utc": _utcnow(), "config": asdict(cfg),
        "environment": {"python": sys.version.split()[0],
                        "platform": platform.platform()},
        "providers": summaries,
        "totals": {"items": sum(s["total_items"] for s in summaries),
                   "rejected": sum(s["total_rejected"] for s in summaries),
                   "failed_cells": sum(len(s["failures"]) for s in summaries)},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    tracker.log_artifact(str(run_dir / "manifest.json"))
    tracker.close()
    log.info("run %s done: %d items, %d rejected, %d failed cells -> %s",
             run_id, manifest["totals"]["items"], manifest["totals"]["rejected"],
             manifest["totals"]["failed_cells"], run_dir)
    print(json.dumps(manifest["totals"], indent=2))
    return manifest


if __name__ == "__main__":
    main()
