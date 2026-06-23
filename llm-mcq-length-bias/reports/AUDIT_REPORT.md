# AUDIT_REPORT.md — Phase 1 Repository Audit

**Project:** The Longest-Answer Heuristic — Answer-Length Bias in LLM-Generated MCQs
**Audit date:** 2026-06-23
**Auditor role:** Research engineering / statistical review / reproducibility
**Scope:** Full repository under `llm-mcq-length-bias/` (code, manuscript, data, results, submission docs).

This report is the entry point for a ten-phase review whose goal is to move the
project from a *well-packaged manuscript* to a *scientifically defensible*
artifact. It maps what exists, verifies what runs, and classifies every weakness
as an **immediate** fix (addressed in this review) or a **long-term** fix
(requires data collection or human-subject work the review cannot perform).

---

## 1. Repository structure map

```
The-Longest-Answer-Heuristic/
├── README.md                         (1-line stub at repo root)
├── .gitignore                        (ignores local real corpora corpus_*.jsonl)
└── llm-mcq-length-bias/              (the actual project)
    ├── README.md                     honest "about the numbers" note already present
    ├── requirements.txt              numpy/scipy/pandas/matplotlib/statsmodels(+requests)
    ├── src/
    │   ├── metrics.py                LAA, E, δ, leakage AUC, logistic, Holm–Bonferroni
    │   ├── synthesize_demo.py        SYNTHETIC corpus generator with injected bias
    │   ├── collect.py                6-provider live harness (+ --dry-run mock)
    │   ├── mitigate.py               auditor + 3 mitigations + hardening pipeline
    │   └── analyze.py                driver: reports, tables, figures, results.json
    ├── data/
    │   ├── synthetic_mcq.jsonl       3,600 synthetic items (the analyzed corpus)
    │   └── corpus_dryrun.jsonl       75 mock items (plumbing test)
    ├── results/
    │   ├── results_synthetic.json    all computed numbers
    │   ├── table_per_model_synthetic.tex
    │   └── table_mitigation_synthetic.tex
    ├── figures/                      6 figures × {png,pdf}
    ├── paper/
    │   ├── main.tex                  two-column manuscript (~770 lines)
    │   ├── references.bib            17 references
    │   └── main.pdf                  compiled manuscript
    └── submission/
        ├── cover_letter.md           templated, honest about synthetic data
        ├── disclosures.md            funding / COI / ethics / CRediT
        ├── data_availability.md      code+synthetic open; real corpus deferred
        └── ai_use_disclosure.md      generative-AI statement
```

**Reproducibility check (performed):** `synthesize_demo.py` regenerates
`synthetic_mcq.jsonl` **byte-identical** (same seed=7); `analyze.py` reproduces
every headline number in `results_synthetic.json` exactly (LAA 0.521, E +0.361,
AUC 0.698, mitigation 71.4 %→2.9 %). The pipeline is genuinely deterministic.
This is a real strength and is uncommon; it is preserved by every change in this
review.

---

## 2. Manuscript structure map

| § | Section | Evidentiary status |
|---|---------|--------------------|
| Abstract | Frames contributions; **explicitly labels results synthetic** | Honest |
| 1 | Introduction + RQ1–RQ4 | RQ4 contains an overclaim ("without degrading item quality") |
| 2 | Related work (item-writing flaws; AQG; LLM biases) | Sound; all citations real (Phase 8) |
| 3 | Formalizing leakage (LAA, E, δ, AUC, logistic) | Definitions sound; logistic inference flawed (Phase 4) |
| 4 | Data-collection harness | Real code; not yet executed against live APIs |
| 5 | Mitigation toolkit | Real code; evaluated only on synthetic ground truth |
| 6 | Experimental setup | Clearly states synthetic corpus, injected bias |
| 7 | Results | All synthetic; labeled "illustrative" throughout |
| 8 | Discussion | Mechanisms framed as hypotheses (good) |
| 9 | Conclusion | Mostly bounded; RQ4 sentence needs care |
| 10 | Limitations | Strong; 7 explicit limitations |
| 11 | Future work | Preregistered real-model + human-subject plan |
| — | Reproducibility / Ethics / Appendix | Present and accurate |

The manuscript is **unusually candid** about the synthetic/real distinction. The
remaining risks are narrow but real: a small number of sentences claim more than
the synthetic evidence supports, and the inferential statistics rest on an
independence assumption that the data structure violates.

---

## 3. Experimental pipeline map

```
synthesize_demo.py ──► data/synthetic_mcq.jsonl ──┐
                                                   ├─► analyze.py ─► results_synthetic.json
collect.py (LIVE, not run) ──► data/corpus_*.jsonl ┘                ├─► *.tex tables
                                                                    ├─► figures/*.{png,pdf}
metrics.py  (imported by analyze, mitigate, stats_robust)           └─► console report
mitigate.py (imported by analyze for before/after hardening)
```

Single entry point (`analyze.py`) consumes a JSONL corpus and emits every
artifact. The **same** driver is meant to run on the real corpus once collected;
only the input file changes. This is good design.

## 4. Dataset generation workflow map

```
MODELS = {Model-A..F : (bias b, base elaboration μ0)}          # injected ground truth
for model × subject × difficulty × n_per_cell(=40):
    answer_index ~ U{0..3}
    for each option j:
        n_clauses ~ Gauss(base_clauses[difficulty] + (b·2.2 if fires else 0), 0.8)
        option_text = core + n_clauses × (qualifier + filler)   # length ∝ n_clauses
shuffle → 3,600 items
```

**Key property (and key caveat):** length is the *only* signal injected. The keyed
option is made longer by appending semantically empty filler clauses. The corpus
therefore contains a known, length-only effect and **no genuine content**, which
is exactly why every downstream number is "illustrative, not a measurement."

## 5. Statistical analysis workflow map

```
compute_report(dataset):
    LAA, E (with bootstrap CIs over items)
    δ mean/SD/effect, Wilcoxon signed-rank
    leakage AUC (Mann–Whitney) + item-level bootstrap CI
    rank distribution
logistic_length_leakage(dataset):
    pool ALL options (N×m rows) → Logit(is_correct ~ z_length)   ⚠ independence assumed
per_group_reports(model | subject | difficulty)
holm_bonferroni(per-model binomial p-values)
```

⚠ **Independence flaw:** the logistic pools `N×m` options as if independent. They
are not (exactly one correct per item; items share per-cell generative
parameters). Addressed in Phase 4 via `stats_robust.py` (cluster-robust SEs,
conditional logit, cluster bootstrap).

## 6. Figure generation workflow map

| Figure | Function (`analyze.py`) | Content |
|--------|-------------------------|---------|
| `fig_exploitability_by_model` | per-model E bars + bootstrap CI | model gradient |
| `fig_rank_distribution` | key length-rank histogram vs 1/k null | rank-1 mass |
| `fig_heatmap` | model × subject E heatmap | per-cell estimator |
| `fig_delta_distribution` | per-item δ histogram | key-longer-than-distractor |
| `fig_mitigation` | E & AUC before/after bars | mitigation effect |

All figures are regenerated deterministically from the corpus; all are captioned
"(illustrative)" / "(synthetic)" in the manuscript.

---

## 7. Strengths

1. **Radical transparency about the synthetic corpus.** The abstract, intro,
   setup, results header, limitations, README, and data-availability statement all
   state that the numbers are synthetic and not real-model measurements. This is
   rare and commendable.
2. **End-to-end determinism / reproducibility.** Verified: byte-identical corpus
   regeneration and exact numeric reproduction.
3. **Clean, well-documented, dependency-light code** with a sensible single-driver
   architecture and an offline `--dry-run` path.
4. **Genuinely novel framing** — an *exploitability* metric and a *generation-time*
   mitigation toolkit for a known psychometric flaw, ported to the LLM setting.
5. **Real, relevant, correctly-attributed literature** (verified in Phase 8),
   including very recent and directly competing work (BenchMarker; the Frontiers
   automation-bias study).
6. **Mature submission scaffolding** (cover letter, disclosures, AI-use, data
   availability) already drafted honestly.

## 8. Weaknesses

| # | Weakness | Severity | Phase |
|---|----------|----------|-------|
| W1 | RQ4 claims mitigation preserves "item quality"; no quality measurement exists, and the deterministic mock rewriter appends meaningless filler (it *degrades* meaning). | High | 3 |
| W2 | Logistic regression treats `N×m` options as independent → anti-conservative SEs/CIs/p-values. | High | 4 |
| W3 | "Closed-loop" validation: metrics are validated by recovering a bias the same code injected; risk of reading circular self-consistency as external validation. | Medium | 5 |
| W4 | No real model-output collection has been run; the entire empirical core is deferred. | High (intrinsic) | 6 |
| W5 | The central exploitability claim ("length reveals the key") is not validated by a predictive model on real data. | High | 7 |
| W6 | Several real references have incomplete metadata (missing authors/DOIs). | Low | 8 |
| W7 | Title ("…as a Threat to Assessment Integrity") asserts a real-world threat the synthetic study cannot establish. | Medium | 9 |
| W8 | Venue framing as an empirical paper is misaligned with the (currently methodological) evidence base. | Medium | 10 |

## 9. Publication blockers

A reputable **empirical** venue would reject on these grounds today:

- **B1 (data):** No real-model data; all quantitative claims are synthetic
  (W4). *Intrinsic* — cannot be removed by editing, only by collection.
- **B2 (statistics):** Inference assumes option independence (W2). *Fixable now.*
- **B3 (claim–evidence gaps):** RQ4 quality claim (W1) and any title/abstract
  wording that implies real-world measurement (W7). *Fixable now.*
- **B4 (construct validation):** Exploitability is asserted, not demonstrated by a
  predictor on real items (W5). *Pipeline + preregistration now; result later.*

Blockers B2 and B3 are addressed in this review. B1 and B4 are reframed honestly
(claims bounded to what synthetic data can support) and equipped with the
infrastructure + preregistered protocol needed to resolve them.

## 10. Immediate fixes (this review)

- **Phase 3:** Remove the "preserves item quality" overclaim; replace with
  evidence-aligned wording. Document in `RQ4_FIX_REPORT.md`.
- **Phase 4:** Add `stats_robust.py` (cluster-robust SEs, conditional logit,
  cluster bootstrap); report corrected uncertainty; update manuscript.
  Document in `STATISTICAL_VALIDITY_REPORT.md`.
- **Phase 5:** Rewrite any sentence that could imply real-world validation; add a
  circularity caveat. Document in `CLOSED_LOOP_ANALYSIS.md`.
- **Phase 6:** Ship a modular, reproducible `data_collection/` package + provenance
  schema. Document in `REAL_COLLECTION_PLAN.md`.
- **Phase 7:** Ship the exploitability ML pipeline (features + 3 baselines + group
  CV) **and a preregistration**, with results withheld until real data exist.
  Document in `EXPLOITABILITY_ANALYSIS.md`.
- **Phase 8:** Complete citation metadata; document every change in
  `CITATION_AUDIT.md`.
- **Phase 9 / 10:** Title and venue recommendations aligned to the real evidence
  base (`TITLE_RECOMMENDATIONS.md`, `VENUE_STRATEGY.md`).

## 11. Long-term fixes (out of scope for editing; require new data)

- Collect a real cross-model corpus with `data_collection/` and re-run `analyze.py`
  + `exploitability.py` on it (resolves B1, B4).
- Run the preregistered human-subject study to convert E from a corpus statistic
  into a measured integrity risk.
- Add a genuine item-quality evaluation (expert rubric / readability / answerability)
  to substantiate any future "quality-preserving mitigation" claim (resolves W1
  empirically rather than by wording).
- Replace the deterministic mock rewriter with a real LLM rewriter and measure the
  mitigation's effect on real items.

---

### Bottom line

The artifact is honest and reproducible but **methodological**, not empirical. Two
publication blockers (statistics, claim–evidence alignment) are removable by
editing and are removed in Phases 3–5/8. The remaining blockers are *evidentiary*
and are handled the only defensible way: by bounding the claims to the synthetic
evidence and shipping the infrastructure + preregistered protocols (Phases 6–7,
9–10) needed to earn the empirical claims later.
