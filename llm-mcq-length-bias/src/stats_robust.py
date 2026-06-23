"""
stats_robust.py
===============
Clustering-aware re-analysis of answer-length leakage.

WHY THIS MODULE EXISTS
----------------------
The pooled length-leakage logistic regression in ``metrics.logistic_length_leakage``
treats every *option* as an independent Bernoulli observation. It is not. The data
have a nested structure:

    option  (the modelled row; m per item)
      └─ item        (exactly ONE of the m options is keyed correct  ->  the
                      labels are mechanically dependent *within* an item)
          └─ cell    (model x subject x difficulty; items in a cell share the
                      same generative parameters)
              └─ model

Treating ``N x m`` options as i.i.d. understates the sampling variance of every
option-level statistic (the leakage AUC, the logistic slope, its p-value and CI).
The point estimates are unaffected; the *uncertainty* is mis-stated, almost always
too small (anti-conservative), so naive p-values and CIs overstate the evidence.

WHAT WE DO ABOUT IT
-------------------
We provide four standard remedies and report them side-by-side so the impact of
the correction is explicit:

  1. ``logistic_naive``            -- the original pooled fit (for reference).
  2. ``logistic_cluster_robust``  -- same fit, cluster-robust (sandwich) SEs.
                                     Clustering at the ITEM level absorbs the
                                     within-item dependence; clustering at the
                                     CELL level additionally absorbs shared
                                     generative structure.
  3. ``conditional_logistic``     -- McFadden conditional logit stratified by
                                     item. This is the *exact* likelihood for the
                                     "one-correct-of-m" design: it conditions on
                                     the within-item competition rather than
                                     assuming independence, so it is the
                                     statistically correct primary model here.
  4. ``clustered_bootstrap_ci``   -- non-parametric CIs that resample whole
                                     clusters (cells). Distribution-free; the most
                                     conservative and assumption-light option.

We deliberately do NOT cluster-robust at the *model* level for inference: there
are only 6 models, far below the ~40-cluster rule of thumb for the sandwich
estimator, so model-level CRVE would itself be unreliable. The cell level (90
clusters) is the appropriate top level for variance estimation; the model level
is handled by the per-model breakdown instead.

All numbers produced here are computed on the SYNTHETIC corpus and inherit its
"illustrative, not a real-model measurement" status. The contribution of this
module is methodological: it fixes *how* uncertainty is estimated, independent of
whose data is in the file.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Callable, Optional

import numpy as np

from metrics import char_len, option_lengths, compute_report, LengthFn


# --------------------------------------------------------------------------- #
# Design-matrix construction
# --------------------------------------------------------------------------- #
@dataclass
class OptionDesign:
    """Long-format, one row per option, with the cluster identifiers attached."""
    z_len: np.ndarray        # standardized option length (the predictor)
    y: np.ndarray            # 1 if the option is the key, else 0
    item_id: np.ndarray      # integer item index (within-item cluster)
    cell_id: np.ndarray      # integer (model x subject x difficulty) cluster
    model_id: np.ndarray     # integer model cluster
    length_sd: float         # SD used to standardize (to express OR per SD)


def build_option_design(dataset: list[dict],
                        length_fn: LengthFn = char_len) -> OptionDesign:
    """Expand a dataset of items into the long option-level design used by every
    estimator below. Cluster ids are derived from item metadata; if a field is
    absent the item falls back to its own singleton cluster."""
    z_raw, y, item_id, cells, models = [], [], [], [], []
    for i, it in enumerate(dataset):
        lens = option_lengths(it, length_fn)
        lab = np.zeros(len(lens))
        lab[it["answer_index"]] = 1.0
        z_raw.append(lens)
        y.append(lab)
        item_id.append(np.full(len(lens), i))
        model = str(it.get("model", "NA"))
        subject = str(it.get("subject", "NA"))
        difficulty = str(it.get("difficulty", "NA"))
        cells.append(np.full(len(lens), f"{model}|{subject}|{difficulty}"))
        models.append(np.full(len(lens), model))

    z_raw = np.concatenate(z_raw)
    y = np.concatenate(y)
    item_id = np.concatenate(item_id).astype(int)
    cell_codes = {c: k for k, c in enumerate(sorted(set(np.concatenate(cells))))}
    model_codes = {c: k for k, c in enumerate(sorted(set(np.concatenate(models))))}
    cell_id = np.array([cell_codes[c] for c in np.concatenate(cells)], dtype=int)
    model_id = np.array([model_codes[c] for c in np.concatenate(models)], dtype=int)

    sd = float(z_raw.std(ddof=1))
    z = (z_raw - z_raw.mean()) / sd
    return OptionDesign(z, y, item_id, cell_id, model_id, sd)


# --------------------------------------------------------------------------- #
# Estimators
# --------------------------------------------------------------------------- #
def _fit_summary(beta: float, se: float, sd: float, label: str) -> dict:
    """Package a slope estimate + SE as odds ratios with a 95% Wald CI."""
    from scipy import stats
    z = beta / se if se > 0 else float("inf")
    p = float(2 * stats.norm.sf(abs(z)))
    lo, hi = beta - 1.96 * se, beta + 1.96 * se
    return {
        "method": label,
        "beta_per_sd": float(beta),
        "se": float(se),
        "z": float(z),
        "p": p,
        "odds_ratio_per_sd": float(np.exp(beta)),
        "or_ci_per_sd": [float(np.exp(lo)), float(np.exp(hi))],
    }


def logistic_naive(d: OptionDesign) -> dict:
    """Pooled logistic with classical (independence-assuming) SEs."""
    import statsmodels.api as sm
    X = sm.add_constant(d.z_len)
    res = sm.Logit(d.y, X).fit(disp=0)
    return _fit_summary(res.params[1], res.bse[1], d.length_sd,
                        "pooled logistic, naive SE (INVALID: assumes independent options)")


def logistic_cluster_robust(d: OptionDesign, level: str = "item") -> dict:
    """Pooled logistic with cluster-robust (sandwich) SEs at ``item`` or ``cell``."""
    import statsmodels.api as sm
    groups = {"item": d.item_id, "cell": d.cell_id, "model": d.model_id}[level]
    X = sm.add_constant(d.z_len)
    res = sm.Logit(d.y, X).fit(disp=0, cov_type="cluster",
                               cov_kwds={"groups": groups})
    out = _fit_summary(res.params[1], res.bse[1], d.length_sd,
                       f"pooled logistic, cluster-robust SE ({level})")
    out["n_clusters"] = int(len(np.unique(groups)))
    return out


def conditional_logistic(d: OptionDesign) -> dict:
    """McFadden conditional logit stratified by item: the exact likelihood for the
    'exactly one correct option of m' design. Conditions out the within-item
    competition, so it needs no independence assumption across options of an item.
    Has no intercept (differenced away by conditioning)."""
    from statsmodels.discrete.conditional_models import ConditionalLogit
    res = ConditionalLogit(d.y, d.z_len.reshape(-1, 1), groups=d.item_id).fit(disp=0)
    out = _fit_summary(res.params[0], res.bse[0], d.length_sd,
                       "conditional logit, stratified by item (EXACT for 1-of-m)")
    out["n_strata"] = int(len(np.unique(d.item_id)))
    return out


def _pooled_auc(z: np.ndarray, y: np.ndarray) -> float:
    from scipy import stats
    pos, neg = (y == 1), (y == 0)
    if pos.sum() == 0 or neg.sum() == 0:
        return 0.5
    order = stats.rankdata(z)
    return float((order[pos].sum() - pos.sum() * (pos.sum() + 1) / 2.0)
                 / (pos.sum() * neg.sum()))


# Lightweight statistics for the cluster bootstrap (no nested resampling inside).
def fast_leakage_auc(dataset: list[dict], length_fn: LengthFn = char_len) -> float:
    """Length-only leakage AUC, computed directly (Mann-Whitney), no bootstrap."""
    lens, labs = [], []
    for it in dataset:
        L = option_lengths(it, length_fn)
        lab = np.zeros(len(L)); lab[it["answer_index"]] = 1.0
        lens.append(L); labs.append(lab)
    return _pooled_auc(np.concatenate(lens), np.concatenate(labs))


def fast_exploitability(dataset: list[dict], length_fn: LengthFn = char_len) -> float:
    """Exploitability E, computed directly from per-item longest-strategy scores."""
    scores, chances = [], []
    for it in dataset:
        L = option_lengths(it, length_fn)
        mx = L.max()
        tied = np.flatnonzero(L == mx)
        scores.append(float(it["answer_index"] in tied) / len(tied))
        chances.append(1.0 / len(L))
    laa = float(np.mean(scores)); chance = float(np.mean(chances))
    return (laa - chance) / (1.0 - chance)


def clustered_bootstrap_ci(dataset: list[dict],
                           statistic: Callable[[list[dict]], float],
                           cluster_key: str = "cell",
                           n_boot: int = 2000,
                           seed: int = 0,
                           length_fn: LengthFn = char_len) -> dict:
    """Cluster bootstrap: resample whole clusters (default = cells) with
    replacement, recompute ``statistic`` on the rebuilt corpus, return a
    percentile 95% CI. Distribution-free and robust to within-cluster dependence
    of arbitrary form."""
    rng = np.random.default_rng(seed)
    clusters: dict[str, list[dict]] = {}
    for it in dataset:
        if cluster_key == "cell":
            key = f"{it.get('model','NA')}|{it.get('subject','NA')}|{it.get('difficulty','NA')}"
        else:
            key = str(it.get(cluster_key, "NA"))
        clusters.setdefault(key, []).append(it)
    keys = list(clusters.keys())
    point = float(statistic(dataset))
    boots = np.empty(n_boot)
    for b in range(n_boot):
        chosen = rng.integers(0, len(keys), len(keys))
        resampled: list[dict] = []
        for c in chosen:
            resampled.extend(clusters[keys[c]])
        boots[b] = statistic(resampled)
    return {"point": point,
            "ci": [float(np.percentile(boots, 2.5)),
                   float(np.percentile(boots, 97.5))],
            "cluster_key": cluster_key, "n_clusters": len(keys), "n_boot": n_boot}


# --------------------------------------------------------------------------- #
# Driver: naive vs corrected, side by side
# --------------------------------------------------------------------------- #
def compare_all(dataset: list[dict], length_fn: LengthFn = char_len,
                n_boot: int = 2000, seed: int = 0) -> dict:
    d = build_option_design(dataset, length_fn)
    logistic = {
        "naive": logistic_naive(d),
        "cluster_robust_item": logistic_cluster_robust(d, "item"),
        "cluster_robust_cell": logistic_cluster_robust(d, "cell"),
        "conditional_logit_item": conditional_logistic(d),
    }
    auc_boot = clustered_bootstrap_ci(
        dataset, lambda ds: fast_leakage_auc(ds, length_fn),
        cluster_key="cell", n_boot=n_boot, seed=seed, length_fn=length_fn)
    expl_boot = clustered_bootstrap_ci(
        dataset, lambda ds: fast_exploitability(ds, length_fn),
        cluster_key="cell", n_boot=n_boot, seed=seed + 1, length_fn=length_fn)
    return {"n_items": len(dataset),
            "n_options": int(len(d.y)),
            "logistic": logistic,
            "leakage_auc_cell_bootstrap": auc_boot,
            "exploitability_cell_bootstrap": expl_boot}


def _load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Clustering-aware leakage re-analysis.")
    ap.add_argument("--data", default="../data/synthetic_mcq.jsonl")
    ap.add_argument("--out", default="../results/stats_robust_synthetic.json")
    ap.add_argument("--n-boot", type=int, default=2000)
    args = ap.parse_args()

    data = _load_jsonl(args.data)
    res = compare_all(data, n_boot=args.n_boot)

    print(f"Items: {res['n_items']}   Options (rows): {res['n_options']}")
    print("\nLogistic slope on standardized option length (odds ratio per +1 SD):")
    print(f"  {'method':<58} {'OR/SD':>7} {'95% CI':>20} {'SE':>8} {'p':>10}")
    for _, r in res["logistic"].items():
        ci = f"[{r['or_ci_per_sd'][0]:.2f}, {r['or_ci_per_sd'][1]:.2f}]"
        print(f"  {r['method']:<58} {r['odds_ratio_per_sd']:>7.3f} {ci:>20} "
              f"{r['se']:>8.4f} {r['p']:>10.1e}")
    ab = res["leakage_auc_cell_bootstrap"]
    eb = res["exploitability_cell_bootstrap"]
    print(f"\nLeakage AUC  : {ab['point']:.3f}  cell-cluster boot 95% CI "
          f"[{ab['ci'][0]:.3f}, {ab['ci'][1]:.3f}]  ({ab['n_clusters']} cells)")
    print(f"Exploitability E: {eb['point']:+.3f}  cell-cluster boot 95% CI "
          f"[{eb['ci'][0]:+.3f}, {eb['ci'][1]:+.3f}]")

    from pathlib import Path
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(res, indent=2))
    print(f"\nWrote {args.out}")
