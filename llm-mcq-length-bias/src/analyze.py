"""
analyze.py
==========
End-to-end analysis for the answer-length-bias study.

Reads an MCQ dataset (JSONL; from synthesize_demo.py for the illustrative demo,
or from collect.py for the real corpus), then:
  1. computes overall + per-model + per-subject + per-difficulty length-bias
     reports and the logistic length-leakage regression;
  2. applies Holm-Bonferroni correction across models;
  3. runs the mitigation pipeline and measures the before/after change in
     exploitability E and leakage AUC;
  4. writes results.json, LaTeX tables, and publication-quality figures.

Usage:
    python analyze.py --data data/synthetic_mcq.jsonl --tag synthetic
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from metrics import (compute_report, per_group_reports, logistic_length_leakage,
                     holm_bonferroni, correct_length_rank, verbosity_differential,
                     char_len)
from mitigate import LengthAuditor, harden_item

# --------------------------------------------------------------------------- #
# Plot style
# --------------------------------------------------------------------------- #
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 200, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "legend.frameon": False, "font.family": "DejaVu Sans",
})
ACCENT = "#2C4A7E"
ACCENT2 = "#C44E52"
GREEN = "#3E8E5A"
GREY = "#8A8A8A"


def load_jsonl(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def fig_exploitability_by_model(per_model, figdir, tag):
    models = list(per_model.keys())
    E = [per_model[m].exploitability for m in models]
    lo = [per_model[m].exploitability_ci[0] for m in models]
    hi = [per_model[m].exploitability_ci[1] for m in models]
    order = np.argsort(E)[::-1]
    models = [models[i] for i in order]
    E = [E[i] for i in order]
    err = [[E[i] - lo[order[i]] for i in range(len(E))],
           [hi[order[i]] - E[i] for i in range(len(E))]]

    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    x = np.arange(len(models))
    bars = ax.bar(x, E, color=ACCENT, width=0.62, yerr=err, capsize=3,
                  error_kw={"elinewidth": 1, "ecolor": "#33333390"})
    ax.axhline(0, color=GREY, lw=1)
    ax.text(len(models) - 0.5, 0.012, "chance (E=0)", color=GREY,
            ha="right", va="bottom", fontsize=9)
    for xi, e in zip(x, E):
        ax.text(xi, e + 0.012, f"{e:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=20, ha="right")
    ax.set_ylabel("Exploitability  E")
    ax.set_title("Surface-heuristic exploitability of LLM-generated MCQs")
    ax.set_ylim(0, max(E) * 1.25)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{figdir}/fig_exploitability_by_model_{tag}.{ext}",
                    bbox_inches="tight")
    plt.close(fig)


def fig_rank_distribution(dataset, figdir, tag, length_fn=char_len):
    ranks = [correct_length_rank(it, length_fn) for it in dataset]
    k = int(np.median([len(it["options"]) for it in dataset]))
    counts = np.array([ranks.count(r) for r in range(1, k + 1)], dtype=float)
    props = counts / counts.sum()
    fig, ax = plt.subplots(figsize=(5.6, 3.7))
    x = np.arange(1, k + 1)
    ax.bar(x, props, color=ACCENT, width=0.6, label="observed")
    ax.axhline(1.0 / k, color=ACCENT2, lw=1.8, ls="--",
               label=f"no-bias null (1/{k})")
    ax.set_xticks(x)
    ax.set_xlabel("Length rank of the correct option  (1 = longest)")
    ax.set_ylabel("Proportion of items")
    ax.set_title("Where the key sits in the length ordering")
    ax.legend()
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{figdir}/fig_rank_distribution_{tag}.{ext}", bbox_inches="tight")
    plt.close(fig)


def fig_heatmap(dataset, figdir, tag):
    models = sorted({it["model"] for it in dataset})
    subjects = sorted({it["subject"] for it in dataset})
    M = np.full((len(models), len(subjects)), np.nan)
    for i, m in enumerate(models):
        for j, s in enumerate(subjects):
            cell = [it for it in dataset if it["model"] == m and it["subject"] == s]
            if cell:
                M[i, j] = compute_report(cell).exploitability
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    im = ax.imshow(M, cmap="RdYlBu_r", aspect="auto", vmin=0,
                   vmax=np.nanmax(M))
    ax.set_xticks(range(len(subjects)))
    ax.set_xticklabels([s.replace("_", " ") for s in subjects], rotation=25, ha="right")
    ax.set_yticks(range(len(models))); ax.set_yticklabels(models)
    for i in range(len(models)):
        for j in range(len(subjects)):
            if not np.isnan(M[i, j]):
                ax.text(j, i, f"{M[i,j]:.2f}", ha="center", va="center",
                        fontsize=8, color="black")
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cb.set_label("Exploitability  E")
    ax.set_title("Exploitability across models and subjects")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{figdir}/fig_heatmap_{tag}.{ext}", bbox_inches="tight")
    plt.close(fig)


def fig_delta_distribution(dataset, figdir, tag, length_fn=char_len):
    deltas = np.array([verbosity_differential(it, length_fn) for it in dataset])
    fig, ax = plt.subplots(figsize=(5.8, 3.7))
    ax.hist(deltas, bins=45, color=ACCENT, alpha=0.85)
    ax.axvline(0, color=GREY, lw=1.5, ls="--", label="no difference")
    ax.axvline(deltas.mean(), color=ACCENT2, lw=2,
               label=f"mean = {deltas.mean():+.1f} chars")
    ax.set_xlabel(r"Verbosity differential  $\delta$  (key $-$ mean distractor, chars)")
    ax.set_ylabel("Number of items")
    ax.set_title("The key is systematically longer than its distractors")
    ax.legend()
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{figdir}/fig_delta_distribution_{tag}.{ext}", bbox_inches="tight")
    plt.close(fig)


def fig_mitigation(before, after, figdir, tag):
    """Grouped bars: E and AUC before vs after hardening."""
    labels = ["Exploitability E", "Leakage AUC"]
    pre = [before["exploitability"], before["leakage_auc"]]
    post = [after["exploitability"], after["leakage_auc"]]
    x = np.arange(len(labels)); w = 0.36
    fig, ax = plt.subplots(figsize=(5.8, 3.9))
    b1 = ax.bar(x - w/2, pre, w, label="before (raw LLM output)", color=ACCENT2)
    b2 = ax.bar(x + w/2, post, w, label="after hardening", color=GREEN)
    ax.axhline(0.5, color=GREY, lw=1, ls=":")
    ax.text(1 + w/2 + 0.02, 0.5, "AUC chance", color=GREY, fontsize=8, va="bottom")
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.012,
                    f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylabel("value")
    ax.set_title("Mitigation removes the exploitable length signal")
    ax.set_ylim(0, max(max(pre), 1.0) * 1.15)
    ax.legend(loc="upper right")
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(f"{figdir}/fig_mitigation_{tag}.{ext}", bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------- #
# LaTeX tables
# --------------------------------------------------------------------------- #
def latex_per_model_table(per_model, logit_by_model, holm, path):
    lines = [
        r"\begin{tabular}{lrrrrr}", r"\toprule",
        r"Model & LAA & $E$ & $\bar\delta$ (ch) & AUC & $p_{\text{Holm}}$\\",
        r"\midrule",
    ]
    for m, rep in sorted(per_model.items(),
                         key=lambda kv: kv[1].exploitability, reverse=True):
        p = holm[m]["p"]
        star = "*" if holm[m]["reject_h0"] else ""
        lines.append(
            f"{m} & {rep.laa:.3f} & {rep.exploitability:+.3f} & "
            f"{rep.delta_mean:+.1f} & {rep.leakage_auc:.3f} & "
            f"{p:.1e}{star}\\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("\n".join(lines))


def latex_mitigation_table(before, after, path):
    def row(name, b, a):
        return f"{name} & {b:.3f} & {a:.3f} & {a-b:+.3f}\\\\"
    lines = [
        r"\begin{tabular}{lrrr}", r"\toprule",
        r"Metric & Before & After & $\Delta$\\", r"\midrule",
        row("Longest-Answer Accuracy", before["laa"], after["laa"]),
        row("Exploitability $E$", before["exploitability"], after["exploitability"]),
        row("Leakage AUC", before["leakage_auc"], after["leakage_auc"]),
        row("Mean differential $\\bar\\delta$ (chars)",
            before["delta_mean"], after["delta_mean"]),
        r"\bottomrule", r"\end{tabular}",
    ]
    Path(path).write_text("\n".join(lines))


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/synthetic_mcq.jsonl")
    ap.add_argument("--tag", default="synthetic")
    ap.add_argument("--figdir", default="figures")
    ap.add_argument("--outdir", default="results")
    args = ap.parse_args()

    Path(args.figdir).mkdir(exist_ok=True)
    Path(args.outdir).mkdir(exist_ok=True)

    data = load_jsonl(args.data)
    print(f"Loaded {len(data)} items from {args.data}")

    overall = compute_report(data)
    print("\n=== OVERALL ===")
    print(overall.summary())

    logit = logistic_length_leakage(data)
    print(f"\nLogistic length-leakage: OR per +1 SD = {logit['odds_ratio_per_sd']:.2f} "
          f"(beta={logit['beta_per_sd']:.3f}, p={logit['p']:.2e})")

    per_model = per_group_reports(data, "model")
    per_subject = per_group_reports(data, "subject")
    per_diff = per_group_reports(data, "difficulty")
    logit_by_model = {m: logistic_length_leakage([it for it in data if it["model"] == m])
                      for m in per_model}
    holm = holm_bonferroni({m: r.laa_binom_p for m, r in per_model.items()})

    # ---- mitigation before/after on the full dataset ----
    print("\nRunning mitigation pipeline (deterministic mock rewriter)...")
    auditor = LengthAuditor()
    hardened = [harden_item(it, auditor) for it in data]
    after_rep = compute_report(hardened)
    before = {"laa": overall.laa, "exploitability": overall.exploitability,
              "leakage_auc": overall.leakage_auc, "delta_mean": overall.delta_mean}
    after = {"laa": after_rep.laa, "exploitability": after_rep.exploitability,
             "leakage_auc": after_rep.leakage_auc, "delta_mean": after_rep.delta_mean}
    aud_before = auditor.audit_dataset(data)
    aud_after = auditor.audit_dataset(hardened)
    print(f"  leaky items: {aud_before['frac_leaky']*100:.1f}% -> "
          f"{aud_after['frac_leaky']*100:.1f}%")
    print(f"  E: {before['exploitability']:+.3f} -> {after['exploitability']:+.3f}")
    print(f"  AUC: {before['leakage_auc']:.3f} -> {after['leakage_auc']:.3f}")

    # ---- figures ----
    fig_exploitability_by_model(per_model, args.figdir, args.tag)
    fig_rank_distribution(data, args.figdir, args.tag)
    fig_heatmap(data, args.figdir, args.tag)
    fig_delta_distribution(data, args.figdir, args.tag)
    fig_mitigation(before, after, args.figdir, args.tag)
    print(f"\nFigures written to {args.figdir}/")

    # ---- tables ----
    latex_per_model_table(per_model, logit_by_model, holm,
                          f"{args.outdir}/table_per_model_{args.tag}.tex")
    latex_mitigation_table(before, after,
                           f"{args.outdir}/table_mitigation_{args.tag}.tex")

    # ---- results.json ----
    def rep_to_dict(r):
        return {"n_items": r.n_items, "k_mean": r.k_mean, "chance": r.chance,
                "laa": r.laa, "laa_ci": r.laa_ci, "exploitability": r.exploitability,
                "exploitability_ci": r.exploitability_ci, "delta_mean": r.delta_mean,
                "delta_effect": r.delta_effect, "delta_wilcoxon_p": r.delta_wilcoxon_p,
                "laa_binom_p": r.laa_binom_p, "leakage_auc": r.leakage_auc,
                "leakage_auc_ci": r.leakage_auc_ci,
                "rank_distribution": r.rank_distribution}
    results = {
        "tag": args.tag, "n_items": len(data),
        "overall": rep_to_dict(overall),
        "logistic": logit,
        "per_model": {m: rep_to_dict(r) for m, r in per_model.items()},
        "per_subject": {s: rep_to_dict(r) for s, r in per_subject.items()},
        "per_difficulty": {d: rep_to_dict(r) for d, r in per_diff.items()},
        "holm_bonferroni": holm,
        "mitigation": {"before": before, "after": after,
                       "frac_leaky_before": aud_before["frac_leaky"],
                       "frac_leaky_after": aud_after["frac_leaky"]},
    }
    Path(f"{args.outdir}/results_{args.tag}.json").write_text(
        json.dumps(results, indent=2))
    print(f"Results written to {args.outdir}/results_{args.tag}.json")
    return results


if __name__ == "__main__":
    main()
