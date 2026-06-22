"""
metrics.py
==========
Reusable metrics for quantifying *answer-length leakage* in multiple-choice
questions (MCQs), i.e. the degree to which the surface length of an option
predicts whether it is the keyed (correct) answer.

These metrics operationalise the "longest-option-corrects" item-writing flaw
(Haladyna, Downing & Rodriguez, 2002) as a measurable, exploitable surface
heuristic and form the empirical core of the accompanying paper.

All functions are dependency-light (numpy + scipy only). A single MCQ item is a
dict:

    {
        "id": "subj/0001",
        "stem": "....",
        "options": ["opt A text", "opt B text", "opt C text", "opt D text"],
        "answer_index": 2,          # 0-based index of the correct option
        # optional metadata: "model", "subject", "difficulty", ...
    }

A dataset is simply a list[dict] of such items.

Length is measured with a pluggable `length_fn`. Two are provided:
  * char_len  -> number of characters (default; tokenizer-free, reproducible)
  * word_len  -> number of whitespace tokens
Token counts from a real tokenizer (e.g. tiktoken) can be substituted by passing
a custom length_fn; conclusions in the paper are reported for both char and word
length and are robust to the choice.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable

import numpy as np
from scipy import stats

# --------------------------------------------------------------------------- #
# Length functions
# --------------------------------------------------------------------------- #
def char_len(text: str) -> int:
    """Characters excluding leading/trailing whitespace."""
    return len(text.strip())


def word_len(text: str) -> int:
    """Whitespace-delimited tokens."""
    return len(text.strip().split())


LengthFn = Callable[[str], float]


# --------------------------------------------------------------------------- #
# Per-item helpers
# --------------------------------------------------------------------------- #
def option_lengths(item: dict, length_fn: LengthFn = char_len) -> np.ndarray:
    return np.array([float(length_fn(o)) for o in item["options"]], dtype=float)


def longest_strategy_score(item: dict, length_fn: LengthFn = char_len) -> float:
    """
    Expected score of a test-taker who always picks the *longest* option,
    breaking ties by uniform random choice among the maximal-length options.

    Returns 1.0 if the correct option is the unique longest, 1/m if it ties with
    m-1 other maximal options, and 0.0 otherwise.
    """
    lens = option_lengths(item, length_fn)
    c = item["answer_index"]
    max_len = lens.max()
    tied = np.flatnonzero(lens == max_len)
    return float(c in tied) / len(tied)


def correct_length_rank(item: dict, length_fn: LengthFn = char_len) -> int:
    """
    Rank of the correct option among k options sorted by *descending* length
    (1 = longest). Ties are broken by average rank so the expectation under the
    no-bias null stays uniform on {1..k}.
    """
    lens = option_lengths(item, length_fn)
    c = item["answer_index"]
    order = stats.rankdata(-lens, method="average")  # 1 = longest
    return int(round(order[c]))


def verbosity_differential(item: dict, length_fn: LengthFn = char_len) -> float:
    """
    delta_i = length(correct) - mean(length(distractors)).
    Positive => the keyed option is longer than the typical distractor.
    """
    lens = option_lengths(item, length_fn)
    c = item["answer_index"]
    distractors = np.delete(lens, c)
    return float(lens[c] - distractors.mean())


# --------------------------------------------------------------------------- #
# Dataset-level metrics
# --------------------------------------------------------------------------- #
@dataclass
class LengthBiasReport:
    n_items: int
    k_mean: float
    chance: float                 # mean 1/k_i (the random-guess baseline)
    laa: float                    # Longest-Answer Accuracy
    laa_ci: tuple[float, float]   # 95% Wilson-ish bootstrap CI
    exploitability: float         # E = (LAA - chance) / (1 - chance)
    exploitability_ci: tuple[float, float]
    delta_mean: float             # mean verbosity differential
    delta_sd: float
    delta_effect: float           # standardised differential (Cohen's d-style)
    delta_wilcoxon_p: float       # H0: median delta = 0
    laa_binom_p: float            # H0: longest-strategy score == chance
    leakage_auc: float            # AUC of length-only key classifier
    leakage_auc_ci: tuple[float, float]
    rank_distribution: dict       # {rank: proportion}
    extra: dict = field(default_factory=dict)

    def summary(self) -> str:
        lo, hi = self.exploitability_ci
        return (
            f"N={self.n_items} items, mean k={self.k_mean:.2f}, chance={self.chance:.3f}\n"
            f"  Longest-Answer Accuracy (LAA) = {self.laa:.3f} "
            f"[{self.laa_ci[0]:.3f}, {self.laa_ci[1]:.3f}]\n"
            f"  Exploitability E              = {self.exploitability:+.3f} "
            f"[{lo:+.3f}, {hi:+.3f}]   (0=chance, 1=always longest)\n"
            f"  Verbosity differential delta  = {self.delta_mean:+.2f} chars "
            f"(SD={self.delta_sd:.2f}, d={self.delta_effect:+.2f}, "
            f"Wilcoxon p={self.delta_wilcoxon_p:.2e})\n"
            f"  Length-leakage AUC            = {self.leakage_auc:.3f} "
            f"[{self.leakage_auc_ci[0]:.3f}, {self.leakage_auc_ci[1]:.3f}]\n"
            f"  LAA vs chance binomial p      = {self.laa_binom_p:.2e}"
        )


def _bootstrap_ci(values: np.ndarray, stat: Callable[[np.ndarray], float],
                  n_boot: int = 2000, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(values)
    if n == 0:
        return (float("nan"), float("nan"))
    boots = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        boots[b] = stat(values[idx])
    return (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5)))


def _auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """
    AUC via the Mann-Whitney U relationship. labels in {0,1}.
    Returns 0.5 if one class is empty.
    """
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    # rank-based AUC (handles ties correctly)
    order = stats.rankdata(scores)
    rank_pos = order[labels == 1].sum()
    auc = (rank_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))
    return float(auc)


def compute_report(dataset: list[dict],
                   length_fn: LengthFn = char_len,
                   seed: int = 0) -> LengthBiasReport:
    """Compute the full length-bias report for a dataset of MCQ items."""
    if not dataset:
        raise ValueError("empty dataset")

    ks = np.array([len(it["options"]) for it in dataset], dtype=float)
    chance = float(np.mean(1.0 / ks))

    # Longest-answer strategy
    long_scores = np.array(
        [longest_strategy_score(it, length_fn) for it in dataset], dtype=float
    )
    laa = float(long_scores.mean())
    laa_ci = _bootstrap_ci(long_scores, np.mean, seed=seed)

    # Exploitability E and its CI (propagate the bootstrap through the transform)
    def _expl(v):
        m = v.mean()
        return (m - chance) / (1.0 - chance)
    exploit = _expl(long_scores)
    exploit_ci = _bootstrap_ci(long_scores, _expl, seed=seed + 1)

    # Verbosity differential
    deltas = np.array(
        [verbosity_differential(it, length_fn) for it in dataset], dtype=float
    )
    delta_mean = float(deltas.mean())
    delta_sd = float(deltas.std(ddof=1)) if len(deltas) > 1 else 0.0
    delta_effect = delta_mean / delta_sd if delta_sd > 0 else 0.0
    if np.allclose(deltas, 0):
        wil_p = 1.0
    else:
        try:
            wil_p = float(stats.wilcoxon(deltas, zero_method="wilcox",
                                         alternative="two-sided").pvalue)
        except ValueError:
            wil_p = 1.0

    # Binomial-style test: is the longest strategy better than chance?
    # Use a normal approximation on the per-item scores (handles fractional ties).
    if long_scores.std(ddof=1) > 0:
        t = (laa - chance) / (long_scores.std(ddof=1) / math.sqrt(len(long_scores)))
        binom_p = float(2 * stats.t.sf(abs(t), df=len(long_scores) - 1))
    else:
        binom_p = 0.0 if laa != chance else 1.0

    # Length-leakage AUC: pool all options, label = is_correct, score = length
    all_len, all_lab = [], []
    for it in dataset:
        lens = option_lengths(it, length_fn)
        lab = np.zeros(len(lens))
        lab[it["answer_index"]] = 1
        all_len.append(lens)
        all_lab.append(lab)
    all_len = np.concatenate(all_len)
    all_lab = np.concatenate(all_lab)
    leakage_auc = _auc(all_len, all_lab)

    # bootstrap CI for AUC at the *item* level (resample items, not options)
    rng = np.random.default_rng(seed + 2)
    item_lens = [option_lengths(it, length_fn) for it in dataset]
    item_labs = []
    for it in dataset:
        lab = np.zeros(len(it["options"]))
        lab[it["answer_index"]] = 1
        item_labs.append(lab)
    aucs = []
    n = len(dataset)
    for _ in range(1000):
        idx = rng.integers(0, n, n)
        L = np.concatenate([item_lens[i] for i in idx])
        Y = np.concatenate([item_labs[i] for i in idx])
        aucs.append(_auc(L, Y))
    auc_ci = (float(np.percentile(aucs, 2.5)), float(np.percentile(aucs, 97.5)))

    # Correct-option length-rank distribution
    ranks = [correct_length_rank(it, length_fn) for it in dataset]
    uniq, counts = np.unique(ranks, return_counts=True)
    rank_dist = {int(r): float(c) / len(ranks) for r, c in zip(uniq, counts)}

    return LengthBiasReport(
        n_items=len(dataset),
        k_mean=float(ks.mean()),
        chance=chance,
        laa=laa,
        laa_ci=laa_ci,
        exploitability=exploit,
        exploitability_ci=exploit_ci,
        delta_mean=delta_mean,
        delta_sd=delta_sd,
        delta_effect=delta_effect,
        delta_wilcoxon_p=wil_p,
        laa_binom_p=binom_p,
        leakage_auc=leakage_auc,
        leakage_auc_ci=auc_ci,
        rank_distribution=rank_dist,
    )


def logistic_length_leakage(dataset: list[dict],
                            length_fn: LengthFn = char_len) -> dict:
    """
    Fit a logistic regression  P(option is correct) ~ standardized length, pooled
    over all options. Reports the log-odds per +1 SD of length and per +10 chars,
    with a 95% CI. Uses statsmodels if available, otherwise a tiny IRLS solver.

    A positive, significant coefficient is direct evidence that length leaks the
    answer key (construct-irrelevant variance).
    """
    X_raw, y = [], []
    for it in dataset:
        lens = option_lengths(it, length_fn)
        lab = np.zeros(len(lens))
        lab[it["answer_index"]] = 1
        X_raw.append(lens)
        y.append(lab)
    X_raw = np.concatenate(X_raw)
    y = np.concatenate(y)
    mu, sd = X_raw.mean(), X_raw.std(ddof=1)
    Xz = (X_raw - mu) / sd

    try:
        import statsmodels.api as sm
        Xd = sm.add_constant(Xz)
        res = sm.Logit(y, Xd).fit(disp=0)
        beta = float(res.params[1])
        se = float(res.bse[1])
        p = float(res.pvalues[1])
    except Exception:
        # minimal IRLS fallback
        Xd = np.column_stack([np.ones_like(Xz), Xz])
        beta_vec = np.zeros(2)
        for _ in range(100):
            eta = Xd @ beta_vec
            p_hat = 1 / (1 + np.exp(-eta))
            W = p_hat * (1 - p_hat) + 1e-9
            z = eta + (y - p_hat) / W
            beta_vec = np.linalg.solve((Xd.T * W) @ Xd, (Xd.T * W) @ z)
        eta = Xd @ beta_vec
        p_hat = 1 / (1 + np.exp(-eta))
        W = p_hat * (1 - p_hat) + 1e-9
        cov = np.linalg.inv((Xd.T * W) @ Xd)
        beta = float(beta_vec[1]); se = float(np.sqrt(cov[1, 1]))
        zstat = beta / se
        p = float(2 * stats.norm.sf(abs(zstat)))

    ci = (beta - 1.96 * se, beta + 1.96 * se)
    or_per_sd = math.exp(beta)
    beta_per10 = beta * (10.0 / sd)         # log-odds per +10 raw length units
    return {
        "beta_per_sd": beta,
        "se": se,
        "p": p,
        "ci_per_sd": ci,
        "odds_ratio_per_sd": or_per_sd,
        "beta_per_10_units": beta_per10,
        "odds_ratio_per_10_units": math.exp(beta_per10),
        "length_sd": float(sd),
    }


def per_group_reports(dataset: list[dict], group_key: str,
                      length_fn: LengthFn = char_len) -> dict[str, LengthBiasReport]:
    """Compute a report per value of a metadata field (e.g. 'model' or 'subject')."""
    groups: dict[str, list[dict]] = {}
    for it in dataset:
        groups.setdefault(str(it.get(group_key, "NA")), []).append(it)
    return {g: compute_report(items, length_fn) for g, items in groups.items()}


def holm_bonferroni(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm-Bonferroni step-down correction over a dict {label: p}."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    out, reject_all = {}, True
    for rank, (label, p) in enumerate(items):
        thresh = alpha / (m - rank)
        reject = reject_all and (p <= thresh)
        reject_all = reject
        out[label] = {"p": p, "threshold": thresh, "reject_h0": reject}
    return out


if __name__ == "__main__":
    # tiny self-test
    demo = [
        {"id": "t1", "options": ["Paris", "The capital city of France, Paris",
                                 "Lyon", "Nice"], "answer_index": 1},
        {"id": "t2", "options": ["A", "BB", "CCC is the precise answer here", "D"],
         "answer_index": 2},
    ]
    rep = compute_report(demo)
    print(rep.summary())
    print("logistic:", logistic_length_leakage(demo))
