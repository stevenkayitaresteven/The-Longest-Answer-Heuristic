"""
mitigate.py
===========
Algorithms that detect and neutralise answer-length leakage in MCQs.

Four components + an orchestration pipeline:

  (A) LengthAuditor          -- a generation-time GATE. Computes the leakage
                                metrics and flags individual items whose keyed
                                option is recoverable from length alone.
  (B) length_balanced_rewrite_plan
                             -- deterministic planner that turns a flagged item
                                into a constrained rewrite SPEC + an LLM prompt
                                that shortens/lengthens options into a common
                                length band WITHOUT changing which option is
                                correct. (LLM call is pluggable.)
  (C) adversarial_distractor_prompt / length_match_distractors
                             -- length-MATCHED adversarial distractor generation:
                                forces distractors to match the key in length and
                                specificity (kills the "longest = key" cue).
  (D) balance_key_length_rank / shuffle_options
                             -- FORM-level fix: randomise option order (defeats
                                position/selection bias, cf. Zheng et al. 2024)
                                and balance which length-rank holds the key across
                                a whole form so "pick longest" -> chance.

  harden_item / harden_form  -- combine the above into a generate->audit->repair
                                ->re-audit loop.

LLM dependency
--------------
Steps that need a model to *rewrite text* take an `llm_fn: Callable[[str], str]`
callback, so any provider (Anthropic/OpenAI/Google/...) can be plugged in. A
deterministic `mock_llm_rewrite` is provided so the pipeline runs end-to-end in
the demo and yields reproducible before/after numbers. Swap it for a real model
in production.
"""
from __future__ import annotations

import copy
import random
import re
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np

from metrics import (char_len, word_len, option_lengths, compute_report,
                     verbosity_differential, longest_strategy_score, LengthFn)


# ===========================================================================
# (A) Length auditor / gate
# ===========================================================================
@dataclass
class ItemFlag:
    item_id: str
    leaky: bool
    reason: str
    correct_is_longest: bool
    delta: float                 # verbosity differential
    ratio: float                 # len(correct) / mean(len(distractors))


class LengthAuditor:
    """
    Flags an item as length-leaky if the keyed option is the strict longest AND
    its length exceeds the mean distractor length by more than `ratio_thresh`,
    OR if the verbosity differential exceeds `delta_thresh` (in length units).

    `audit_dataset` additionally returns the dataset-level exploitability so the
    gate can reject an entire generated form that is exploitable on aggregate.
    """

    def __init__(self, length_fn: LengthFn = char_len,
                 ratio_thresh: float = 1.20, delta_thresh: float = 8.0):
        self.length_fn = length_fn
        self.ratio_thresh = ratio_thresh
        self.delta_thresh = delta_thresh

    def audit_item(self, item: dict) -> ItemFlag:
        lens = option_lengths(item, self.length_fn)
        c = item["answer_index"]
        distractors = np.delete(lens, c)
        mean_d = distractors.mean() if len(distractors) else 0.0
        ratio = float(lens[c] / mean_d) if mean_d > 0 else float("inf")
        delta = float(lens[c] - mean_d)
        is_longest = bool(lens[c] == lens.max() and (lens == lens.max()).sum() == 1)

        leaky = (is_longest and ratio >= self.ratio_thresh) or (delta >= self.delta_thresh)
        reasons = []
        if is_longest and ratio >= self.ratio_thresh:
            reasons.append(f"key is unique-longest and {ratio:.2f}x mean distractor")
        if delta >= self.delta_thresh:
            reasons.append(f"verbosity differential {delta:+.1f} >= {self.delta_thresh}")
        reason = "; ".join(reasons) if reasons else "balanced"
        return ItemFlag(item.get("id", "?"), leaky, reason, is_longest, delta, ratio)

    def audit_dataset(self, dataset: list[dict]) -> dict:
        flags = [self.audit_item(it) for it in dataset]
        rep = compute_report(dataset, self.length_fn)
        n_leaky = sum(f.leaky for f in flags)
        return {
            "n_items": len(dataset),
            "n_leaky": n_leaky,
            "frac_leaky": n_leaky / len(dataset) if dataset else 0.0,
            "exploitability": rep.exploitability,
            "leakage_auc": rep.leakage_auc,
            "flags": flags,
        }


# ===========================================================================
# (B) Length-balanced rewriting (planner + prompt; LLM call is pluggable)
# ===========================================================================
def target_length_band(item: dict, length_fn: LengthFn = char_len,
                       tol: float = 0.18) -> tuple[float, float]:
    """
    Band built around the MEDIAN option length (robust to one long key), widened
    by +/- tol. Rewrites aim to bring every option inside this band, which removes
    length as a discriminating signal.
    """
    lens = option_lengths(item, length_fn)
    med = float(np.median(lens))
    return med * (1 - tol), med * (1 + tol)


def length_balanced_rewrite_plan(item: dict, length_fn: LengthFn = char_len
                                 ) -> dict:
    """
    Produce, for each option, a target length and an action (shorten/lengthen/keep)
    plus a single LLM prompt that requests a meaning-preserving, length-balanced
    rewrite. Crucially, the prompt forbids making the correct option the longest.
    """
    lo, hi = target_length_band(item, length_fn)
    target = (lo + hi) / 2.0
    lens = option_lengths(item, length_fn)
    specs = []
    for j, (o, L) in enumerate(zip(item["options"], lens)):
        if L < lo:
            action = "lengthen"
        elif L > hi:
            action = "shorten"
        else:
            action = "keep"
        specs.append({"index": j, "current_len": float(L),
                      "target_len": round(target), "action": action})

    prompt = _rewrite_prompt(item, lo, hi)
    return {"band": (lo, hi), "target": target, "specs": specs, "prompt": prompt}


def _rewrite_prompt(item: dict, lo: float, hi: float) -> str:
    opts = "\n".join(f"  ({chr(65+j)}) {o}" for j, o in enumerate(item["options"]))
    return (
        "You are an assessment editor. Rewrite the answer options so that ALL "
        f"options have a length between {int(lo)} and {int(hi)} characters, while "
        "preserving each option's meaning and, above all, KEEPING THE SAME OPTION "
        "CORRECT.\n"
        "Hard constraints:\n"
        "  1. Do NOT change which option is the correct answer.\n"
        "  2. The correct option must NOT be the longest; make lengths near-equal.\n"
        "  3. Do not add information that changes correctness; only adjust verbosity.\n"
        "  4. Keep distractors plausible and equally elaborated.\n"
        f"Stem: {item.get('stem','')}\n"
        f"Options:\n{opts}\n"
        f"Correct option: ({chr(65+item['answer_index'])})\n"
        "Return the rewritten options as a JSON list of strings in the same order."
    )


# ===========================================================================
# (C) Length-matched adversarial distractor generation
# ===========================================================================
def adversarial_distractor_prompt(stem: str, correct: str, n_distractors: int,
                                  length_fn: LengthFn = char_len,
                                  tol: float = 0.15) -> str:
    L = length_fn(correct)
    lo, hi = int(L * (1 - tol)), int(L * (1 + tol))
    return (
        f"Write {n_distractors} INCORRECT but plausible answer options for the "
        f"question below. Each distractor MUST:\n"
        f"  - be wrong, but believable to a partially-prepared student;\n"
        f"  - have a length between {lo} and {hi} characters (the correct answer "
        f"is {L} characters), so length gives NO clue to the answer;\n"
        f"  - match the correct answer's level of detail and specificity;\n"
        f"  - not be a paraphrase of the correct answer.\n"
        f"Question: {stem}\n"
        f"Correct answer (do not reuse): {correct}\n"
        f"Return exactly {n_distractors} distractors as a JSON list of strings."
    )


def length_match_distractors(correct: str, candidate_distractors: list[str],
                             llm_fn: Optional[Callable[[str], str]] = None,
                             length_fn: LengthFn = char_len,
                             tol: float = 0.15, max_rounds: int = 3) -> list[str]:
    """
    Keep candidate distractors whose length is within tol of the correct answer's
    length; for the rest, request length-constrained rewrites from `llm_fn` (or a
    deterministic mock). Returns a length-matched distractor set.
    """
    L = length_fn(correct)
    lo, hi = L * (1 - tol), L * (1 + tol)
    fn = llm_fn or (lambda c, target=L: mock_llm_resize(c, target, length_fn))

    out = []
    for d in candidate_distractors:
        cur = d
        for _ in range(max_rounds):
            if lo <= length_fn(cur) <= hi:
                break
            cur = fn(cur)
        out.append(cur)
    return out


# ===========================================================================
# (D) Form-level: option-order randomisation + key length-rank balancing
# ===========================================================================
def shuffle_options(item: dict, rng: random.Random) -> dict:
    """Randomly permute options, tracking the new answer index (kills position cue)."""
    item = copy.deepcopy(item)
    perm = list(range(len(item["options"])))
    rng.shuffle(perm)
    item["options"] = [item["options"][p] for p in perm]
    item["answer_index"] = perm.index(item["answer_index"])
    return item


def balance_key_length_rank(form: list[dict], length_fn: LengthFn = char_len,
                            seed: int = 0) -> list[dict]:
    """
    Across a whole form, REWRITE which option is keyed is impossible (correctness
    is fixed), so instead we *reorder option text by length within each item but
    place the key at a balanced length-rank across the form* is also not valid.

    What we CAN safely do at form level: option-order shuffling (already removes
    position cue). To additionally drive the *length* heuristic to chance, this
    function reports the residual key length-rank distribution after items have
    been length-balanced by (B)/(C); if items are already balanced, ranks are ~
    uniform and exploitability ~ 0. It returns the form unchanged but annotated
    with a per-item residual rank so a planner can prioritise the worst items for
    rewriting.
    """
    rng = random.Random(seed)
    out = []
    for it in form:
        it = copy.deepcopy(it)
        lens = option_lengths(it, length_fn)
        order = (-lens).argsort(kind="stable")
        rank = int(np.where(order == it["answer_index"])[0][0]) + 1
        it["_key_length_rank"] = rank
        out.append(it)
    return out


# ===========================================================================
# Deterministic mock LLM (so the demo runs without a real provider)
# ===========================================================================
_PAD = (" furthermore this option is stated in full and precise detail for clarity"
        " across the relevant cases and standard conditions described herein")


def mock_llm_resize(text: str, target_len: float, length_fn: LengthFn = char_len
                    ) -> str:
    """
    Deterministically shrink or grow `text` toward `target_len` characters.
    Shrinking trims trailing clauses; growing appends neutral padding. This is a
    STAND-IN for a meaning-preserving LLM rewrite used only to make the demo
    runnable; a real llm_fn should be used in production.
    """
    cur = length_fn(text)

    def _closest(prev_text, prev_len, next_text, next_len):
        """Pick whichever of two candidates is nearer to target_len."""
        return prev_text if abs(prev_len - target_len) <= abs(next_len - target_len) \
            else next_text

    if cur > target_len:
        # trim word-by-word; stop at the crossing that is closest to target
        words = text.split()
        prev = " ".join(words)
        while len(words) > 2:
            cand_words = words[:-1]
            cand = " ".join(cand_words)
            if length_fn(cand) <= target_len:
                # crossed (or hit) the target: choose nearer of {prev, cand}
                return _closest(prev, length_fn(prev), cand, length_fn(cand)).rstrip(",;:")
            words = cand_words
            prev = cand
        return " ".join(words).rstrip(",;:")
    elif cur < target_len:
        pad_words = _PAD.split()
        out = text
        prev = out
        for w in pad_words:
            cand = out + " " + w
            if length_fn(cand) >= target_len:
                return _closest(prev, length_fn(prev), cand, length_fn(cand))
            out = cand
            prev = cand
        return out
    return text


def mock_llm_rewrite(item: dict, length_fn: LengthFn = char_len) -> dict:
    """
    Deterministic stand-in for a length-balancing LLM rewrite of a whole item:
    resize every option toward the band centre while keeping the same key.
    """
    item = copy.deepcopy(item)
    lo, hi = target_length_band(item, length_fn)
    target = (lo + hi) / 2.0
    item["options"] = [mock_llm_resize(o, target, length_fn) for o in item["options"]]
    return item


# ===========================================================================
# Orchestration
# ===========================================================================
def harden_item(item: dict,
                auditor: Optional[LengthAuditor] = None,
                llm_rewrite: Optional[Callable[[dict], dict]] = None,
                length_fn: LengthFn = char_len,
                max_rounds: int = 2) -> dict:
    """
    generate -> audit -> (if leaky) length-balanced rewrite -> re-audit, looped.
    Returns the hardened item (or the original if already balanced).
    """
    auditor = auditor or LengthAuditor(length_fn)
    rewrite = llm_rewrite or (lambda it: mock_llm_rewrite(it, length_fn))
    cur = item
    for _ in range(max_rounds):
        flag = auditor.audit_item(cur)
        if not flag.leaky:
            return cur
        cur = rewrite(cur)
    return cur


def harden_form(form: list[dict],
                auditor: Optional[LengthAuditor] = None,
                llm_rewrite: Optional[Callable[[dict], dict]] = None,
                length_fn: LengthFn = char_len,
                shuffle: bool = True, seed: int = 0) -> list[dict]:
    """Apply per-item hardening, then option-order shuffling, to a whole form."""
    auditor = auditor or LengthAuditor(length_fn)
    rng = random.Random(seed)
    out = [harden_item(it, auditor, llm_rewrite, length_fn) for it in form]
    if shuffle:
        out = [shuffle_options(it, rng) for it in out]
    return out


if __name__ == "__main__":
    # quick before/after on a single leaky item
    item = {
        "id": "demo/0001",
        "stem": "Which statement is correct?",
        "options": [
            "Lyon",
            "Paris is the capital and largest city of France, owing to its long "
            "history as the political and cultural centre of the country",
            "Nice",
            "Marseille",
        ],
        "answer_index": 1,
    }
    aud = LengthAuditor()
    print("BEFORE:", aud.audit_item(item))
    hardened = harden_item(item)
    print("AFTER :", aud.audit_item(hardened))
    print("lengths before:", option_lengths(item).round(0))
    print("lengths after :", option_lengths(hardened).round(0))
