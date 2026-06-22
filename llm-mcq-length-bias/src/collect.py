"""
collect.py
==========
Harness to build the REAL cross-model MCQ corpus by querying frontier chat
assistants and saving their generated items in the standard schema used by
metrics.py / analyze.py / mitigate.py.

>>> THIS IS THE STEP THAT MUST BE RUN BY A HUMAN WITH API ACCESS. <<<
The accompanying sandbox cannot run the live path (no API keys; outbound network
is restricted). Use `--dry-run` to test the plumbing; use a provider flag with
the matching API key in your environment to collect real data.

Providers & environment variables
----------------------------------
  anthropic   ANTHROPIC_API_KEY      (Claude)
  openai      OPENAI_API_KEY         (ChatGPT / GPT-*)
  google      GOOGLE_API_KEY         (Gemini)
  xai         XAI_API_KEY            (Grok)
  deepseek    DEEPSEEK_API_KEY       (DeepSeek)
  perplexity  PERPLEXITY_API_KEY     (Perplexity)

Endpoints and model IDs change frequently; verify each against current provider
docs before a run. The OpenAI-compatible adapter covers xai/deepseek/perplexity
(and OpenAI) by changing base_url + model.

Experimental hygiene that makes results publishable
---------------------------------------------------
  * Fixed prompt template, fixed k, fixed decoding params (temperature, seed
    where supported) -> logged into every record for reproducibility.
  * Balanced design: every (model x subject x difficulty) cell gets the same
    number of items.
  * The generation prompt does NOT mention length, so any length signal in the
    output is the model's own behaviour, not an artefact of the instruction.
  * The model is asked to mark the correct option; we DO NOT trust the model's
    own answering — the key is taken from the generation, and downstream metrics
    only use option text + the key index.

Usage
-----
    python collect.py --provider anthropic --model claude-... \
        --n-per-cell 30 --out data/corpus_claude.jsonl
    python collect.py --dry-run --out data/corpus_dryrun.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

SUBJECTS = ["history", "biology", "computer_science", "economics", "geography"]
DIFFICULTIES = ["easy", "medium", "hard"]

GEN_PROMPT = """You are writing exam content. Produce exactly {n} multiple-choice \
questions on the topic of {subject} at {difficulty} difficulty for an \
undergraduate course.

Requirements:
- Each question has exactly {k} answer options.
- Exactly one option is correct.
- Options should be plausible and academically appropriate.

Return ONLY valid JSON: a list of {n} objects, each:
{{"stem": "...", "options": ["...","...","...","..."], "answer_index": <0-based int>}}
No commentary, no markdown fences."""


# --------------------------------------------------------------------------- #
# Robust JSON extraction from a model response
# --------------------------------------------------------------------------- #
def parse_items(text: str, k: int) -> list[dict]:
    """Extract a JSON list of MCQ dicts from a (possibly messy) model response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    # try direct parse, else find the outermost [...] block
    candidates = []
    try:
        candidates = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if m:
            try:
                candidates = json.loads(m.group(0))
            except json.JSONDecodeError:
                return []
    out = []
    for obj in candidates if isinstance(candidates, list) else []:
        if not isinstance(obj, dict):
            continue
        opts = obj.get("options")
        ai = obj.get("answer_index")
        if (isinstance(opts, list) and len(opts) == k
                and all(isinstance(o, str) and o.strip() for o in opts)
                and isinstance(ai, int) and 0 <= ai < k):
            out.append({"stem": str(obj.get("stem", "")).strip(),
                        "options": [o.strip() for o in opts],
                        "answer_index": ai})
    return out


# --------------------------------------------------------------------------- #
# Provider adapters  (lazy-import requests so dry-run needs no deps)
# --------------------------------------------------------------------------- #
def _require_requests():
    try:
        import requests  # noqa
        return requests
    except ImportError:
        sys.exit("The live path needs `requests`  (pip install requests).")


def call_anthropic(prompt: str, model: str, temperature: float, max_tokens: int):
    requests = _require_requests()
    key = os.environ["ANTHROPIC_API_KEY"]
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": model, "max_tokens": max_tokens, "temperature": temperature,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    blocks = r.json()["content"]
    return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


def call_openai_compatible(prompt: str, model: str, temperature: float,
                           max_tokens: int, base_url: str, key_env: str):
    """OpenAI / xAI / DeepSeek / Perplexity all speak the OpenAI chat schema."""
    requests = _require_requests()
    key = os.environ[key_env]
    r = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "temperature": temperature, "max_tokens": max_tokens,
              "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call_google(prompt: str, model: str, temperature: float, max_tokens: int):
    requests = _require_requests()
    key = os.environ["GOOGLE_API_KEY"]
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={key}")
    r = requests.post(
        url, headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": temperature,
                                   "maxOutputTokens": max_tokens}},
        timeout=120,
    )
    r.raise_for_status()
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


PROVIDERS = {
    "anthropic": lambda p, m, t, mt: call_anthropic(p, m, t, mt),
    "openai":    lambda p, m, t, mt: call_openai_compatible(
        p, m, t, mt, "https://api.openai.com/v1", "OPENAI_API_KEY"),
    "xai":       lambda p, m, t, mt: call_openai_compatible(
        p, m, t, mt, "https://api.x.ai/v1", "XAI_API_KEY"),
    "deepseek":  lambda p, m, t, mt: call_openai_compatible(
        p, m, t, mt, "https://api.deepseek.com", "DEEPSEEK_API_KEY"),
    "perplexity": lambda p, m, t, mt: call_openai_compatible(
        p, m, t, mt, "https://api.perplexity.ai", "PERPLEXITY_API_KEY"),
    "google":    lambda p, m, t, mt: call_google(p, m, t, mt),
}


# --------------------------------------------------------------------------- #
# Dry-run mock (lets the harness be tested without any provider)
# --------------------------------------------------------------------------- #
def mock_call(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    import random
    from synthesize_demo import generate_item, MODELS
    n = int(re.search(r"exactly (\d+) multiple", prompt).group(1))
    subject = re.search(r"topic of (\w+)", prompt).group(1)
    difficulty = re.search(r"at (\w+) difficulty", prompt).group(1)
    rng = random.Random(hash((model, subject, difficulty)) & 0xFFFF)
    label = list(MODELS)[0]
    items = [generate_item(label, subject, difficulty, i, rng) for i in range(n)]
    payload = [{"stem": it["stem"], "options": it["options"],
                "answer_index": it["answer_index"]} for it in items]
    return json.dumps(payload)


# --------------------------------------------------------------------------- #
# Collection loop
# --------------------------------------------------------------------------- #
@dataclass
class RunConfig:
    provider: str
    model: str
    k: int
    n_per_cell: int
    temperature: float
    max_tokens: int
    dry_run: bool


def collect(cfg: RunConfig, out_path: str) -> None:
    caller = mock_call if cfg.dry_run else PROVIDERS[cfg.provider]
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with out.open("w", encoding="utf-8") as f:
        for subject in SUBJECTS:
            for difficulty in DIFFICULTIES:
                prompt = GEN_PROMPT.format(n=cfg.n_per_cell, subject=subject,
                                           difficulty=difficulty, k=cfg.k)
                try:
                    raw = caller(prompt, cfg.model, cfg.temperature, cfg.max_tokens)
                except Exception as e:  # network / quota / parse robustness
                    print(f"  [warn] {subject}/{difficulty}: {e}", file=sys.stderr)
                    continue
                items = parse_items(raw, cfg.k)
                for idx, it in enumerate(items):
                    it.update({
                        "id": f"{cfg.model}/{subject}/{difficulty}/{idx:04d}",
                        "model": cfg.model, "provider": cfg.provider,
                        "subject": subject, "difficulty": difficulty,
                        "temperature": cfg.temperature, "k": cfg.k,
                    })
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
                    written += 1
                print(f"  {cfg.provider}:{cfg.model} {subject}/{difficulty}: "
                      f"{len(items)} items")
                if not cfg.dry_run:
                    time.sleep(1.0)  # be gentle with rate limits
    print(f"Wrote {written} items -> {out_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=list(PROVIDERS), default="anthropic")
    ap.add_argument("--model", default="MODEL-ID-HERE")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--n-per-cell", type=int, default=30)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=4000)
    ap.add_argument("--dry-run", action="store_true",
                    help="use a built-in mock; no API key or network needed")
    ap.add_argument("--out", default="data/corpus.jsonl")
    args = ap.parse_args()

    cfg = RunConfig(args.provider, args.model, args.k, args.n_per_cell,
                    args.temperature, args.max_tokens, args.dry_run)
    print("Run config:", json.dumps(asdict(cfg), indent=2))
    if not args.dry_run and args.model == "MODEL-ID-HERE":
        sys.exit("Set --model to a real model ID (see provider docs), or use --dry-run.")
    collect(cfg, args.out)


if __name__ == "__main__":
    main()
