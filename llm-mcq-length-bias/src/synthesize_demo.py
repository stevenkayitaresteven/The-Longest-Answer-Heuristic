"""
synthesize_demo.py
==================
Generates a SYNTHETIC MCQ dataset with a *tunable, injected* answer-length bias.

PURPOSE & HONESTY NOTE
----------------------
This module does NOT contain data collected from real language models. It exists
so the full analysis + mitigation pipeline can be run end-to-end and produce real,
reproducible figures/tables for the manuscript's "pipeline demonstration" while we
wait for the real cross-model corpus to be collected with `collect.py`.

Every figure produced from this data is explicitly labelled "ILLUSTRATIVE
(SYNTHETIC)" in the paper. To produce the paper's *empirical* results, replace
the output of this script with the corpus collected by `collect.py` (same schema)
and re-run `analyze.py` / `mitigate.py`.

The generator deliberately reproduces the structure of a real audit:
  * several "models" (Claude/GPT/Gemini/Grok/DeepSeek/Perplexity placeholders),
  * several subjects (history, biology, CS, ...),
  * a per-model length-bias strength `b` that controls how much longer the keyed
    option tends to be than distractors (b=0 -> no bias, b large -> strong bias).
The injected biases below are arbitrary stand-ins, NOT claims about any vendor.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

# --------------------------------------------------------------------------- #
# Configuration: placeholder model names and their *injected* (fake) bias.
# These numbers are stand-ins for a controllable demo, NOT measurements.
# --------------------------------------------------------------------------- #
MODELS = {
    # model label : (length-bias strength b, base elaboration mu0)
    "Model-A": (0.85, 60),
    "Model-B": (0.70, 58),
    "Model-C": (0.55, 55),
    "Model-D": (0.40, 52),
    "Model-E": (0.30, 50),
    "Model-F": (0.20, 48),
}

SUBJECTS = ["history", "biology", "computer_science", "economics", "geography"]
DIFFICULTIES = ["easy", "medium", "hard"]

# Building blocks to synthesise plausible-looking option text of varying length.
_SHORT = ["Paris", "Mitochondria", "O(n log n)", "Inflation", "The Nile",
          "Photosynthesis", "Hash table", "1789", "Tokyo", "Entropy",
          "Gradient descent", "Supply and demand", "DNA", "Recursion", "1945"]
_QUALIFIERS = [
    "which is the process by which",
    "specifically because it accounts for",
    "in the context of the broader system, where",
    "as established by the standard reference framework that",
    "owing to the well-documented mechanism whereby",
    "a result that holds under the usual assumptions and",
    "and this is the precise and complete formulation that",
    "given the conditions described in the prompt, namely that",
]
_FILLERS = [
    "the underlying variables interact predictably",
    "the relationship has been consistently observed across studies",
    "it satisfies all of the stated constraints simultaneously",
    "the canonical definition applies without exception here",
    "the empirical evidence strongly supports this conclusion",
    "it remains valid across the full range of inputs considered",
]


def _make_option(core: str, n_clauses: int, rng: random.Random) -> str:
    """Build an option of controllable length by appending qualifier clauses."""
    parts = [core]
    for _ in range(n_clauses):
        parts.append(rng.choice(_QUALIFIERS))
        parts.append(rng.choice(_FILLERS))
    text = " ".join(parts)
    # light cleanup
    return text[0].upper() + text[1:]


def _clauses_from_length(target_extra_clauses: float, rng: random.Random) -> int:
    """Sample a non-negative integer number of clauses around a target."""
    val = rng.gauss(target_extra_clauses, 0.8)
    return max(0, int(round(val)))


def generate_item(model: str, subject: str, difficulty: str,
                  idx: int, rng: random.Random, k: int = 4) -> dict:
    """
    Generate one synthetic MCQ. The keyed option receives, on average, `b`
    *additional* qualifier clauses relative to distractors, where `b` is the
    model's injected bias strength. With probability proportional to (1-b) the
    bias is suppressed for that item (so the effect is statistical, not absolute).
    """
    b, _mu0 = MODELS[model]
    cores = rng.sample(_SHORT, k)
    answer_index = rng.randrange(k)

    # distractor "elaboration" baseline (in extra clauses)
    base_clauses = {"easy": 0.4, "medium": 0.9, "hard": 1.4}[difficulty]

    options = []
    for j in range(k):
        if j == answer_index:
            # keyed option gets extra clauses scaled by bias strength b,
            # but only "fires" stochastically so the bias is realistic.
            extra = b * 2.2 if rng.random() < (0.4 + 0.6 * b) else 0.0
            n = _clauses_from_length(base_clauses + extra, rng)
        else:
            n = _clauses_from_length(base_clauses, rng)
        options.append(_make_option(cores[j], n, rng))

    return {
        "id": f"{model}/{subject}/{idx:04d}",
        "stem": f"[{subject} | {difficulty}] Which of the following is correct? (Q{idx})",
        "options": options,
        "answer_index": answer_index,
        "model": model,
        "subject": subject,
        "difficulty": difficulty,
    }


def generate_dataset(n_per_cell: int = 40, seed: int = 7) -> list[dict]:
    """
    Produce a dataset over models x subjects x difficulties.
    Default: 6 models x 5 subjects x 3 difficulties x 40 = 3,600 items.
    """
    rng = random.Random(seed)
    data = []
    for model in MODELS:
        for subject in SUBJECTS:
            for difficulty in DIFFICULTIES:
                for i in range(n_per_cell):
                    data.append(generate_item(model, subject, difficulty, i, rng))
    rng.shuffle(data)
    return data


def main(out_path: str = "data/synthetic_mcq.jsonl", n_per_cell: int = 40,
         seed: int = 7) -> None:
    data = generate_dataset(n_per_cell=n_per_cell, seed=seed)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Wrote {len(data)} synthetic items -> {out_path}")
    print("Models:", ", ".join(MODELS))
    print("NOTE: synthetic/illustrative data only — not collected from real models.")


if __name__ == "__main__":
    main()
