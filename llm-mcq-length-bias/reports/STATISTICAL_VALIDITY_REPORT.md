# STATISTICAL_VALIDITY_REPORT.md — Phase 4: Clustering & Non-Independence

## 1. Original method

`metrics.logistic_length_leakage()` pools **every option of every item** into one
design matrix and fits

```
logit P(option is keyed correct) = β₀ + β₁ · z(length)
```

over `N × m = 3600 × 4 = 14,400` rows, with classical (model-based) standard
errors. The reported leakage AUC's confidence interval is a bootstrap that
resamples **items** (good), but the headline logistic `p ≈ 0`, its SE
(`0.0212`), and the OR-per-SD CI `[2.16, 2.35]` come from the pooled fit. The
Wilcoxon test on the verbosity differential treats the `3,600` per-item δ values
as independent.

## 2. The problem: the observations are not independent

The data are hierarchically nested:

```
option   (modelled row; m per item)
  └─ item     ← EXACTLY ONE option is keyed ⇒ labels are mechanically dependent
      └─ cell ← (model×subject×difficulty); 40 items share generative parameters
          └─ model ← bias strength b is constant within a model
```

Two distinct violations follow:

1. **Within-item dependence (the design).** Within an item the labels satisfy
   `Σⱼ yᵢⱼ = 1`. The options compete; knowing three are wrong forces the fourth.
   A pooled Bernoulli likelihood that pretends the 14,400 rows are i.i.d. is the
   wrong likelihood for a "one-correct-of-m" design.

2. **Between-item, within-cluster dependence (the generative process).** Items in
   a cell share `b`, `base_clauses`, and the option-construction grammar, so their
   length signals are positively correlated. Positive intra-cluster correlation
   makes the **effective sample size far smaller than 14,400**; classical SEs,
   which scale like `1/√n`, are correspondingly **too small** (anti-conservative).

The consequence is specifically about **uncertainty, not point estimates**: the
slope/AUC point values are (asymptotically) fine, but their SEs, p-values, and CIs
are understated. On a real corpus with a weaker effect this is exactly the regime
where a spurious "significant" result is manufactured.

## 3. Corrected method (implemented in `src/stats_robust.py`)

We do **not** guess a single fix; we apply the standard menu and report it
side-by-side so the reader sees the correction's size.

| Estimator | What it corrects | Why it is appropriate here |
|-----------|------------------|----------------------------|
| **Conditional logit, stratified by item** (`ConditionalLogit`) | Within-item dependence (#1), *exactly* | McFadden's choice model is the exact likelihood for "one correct of m": it conditions on the within-item competition, differencing out a per-item intercept. **Primary model.** |
| **Cluster-robust (sandwich) SEs at the item level** | Within-item dependence (#1) | Huber–White CRVE with item clusters; assumption-light, keeps the pooled point estimate. |
| **Cluster-robust SEs at the cell level** | Between-item dependence (#2) | Cells are the level at which generative parameters are shared; 90 clusters is adequate for CRVE. |
| **Cluster bootstrap, resampling cells** | #1 and #2, distribution-free | Resamples whole cells with replacement; no parametric assumption on the correlation structure. Applied to AUC and E. |

**Deliberate non-choice:** we do **not** cluster-robust at the *model* level for
inference. With only 6 models the sandwich estimator is unreliable (the
≈40-cluster rule of thumb). Model-level variability is instead reported through
the per-model breakdown. This is stated in the manuscript's Procedure paragraph.

### Mathematical justification (sketch)

- **Conditional logit.** For stratum (item) `i` with one positive at index `kᵢ`,
  conditioning on "exactly one success" yields the likelihood
  `Π_i exp(β·zᵢₖᵢ) / Σⱼ exp(β·zᵢⱼ)`, free of the per-item nuisance intercept and
  of any assumption that options are independent draws. This is the multinomial
  logit / Bradley–Terry form for choosing the key by length.
- **CRVE.** `V_cluster(β̂) = (X'WX)⁻¹ (Σ_g X_g' u_g u_g' X_g) (X'WX)⁻¹`, summing the
  meat over clusters `g` so arbitrary within-cluster correlation is absorbed.
  Consistent as the number of clusters → ∞.
- **Cluster bootstrap.** Resampling clusters (not rows) preserves the
  within-cluster dependence in each replicate, so the percentile interval has
  correct coverage under exchangeable clusters.

## 4. Impact on the conclusions (synthetic corpus)

Computed by `python stats_robust.py` (also embedded in
`results/results_synthetic.json → robust_inference`):

| Quantity | Naive (as published) | Corrected | Effect of correction |
|----------|----------------------|-----------|----------------------|
| OR per SD, **point** | 2.253 | 2.253 (pooled) / **2.610 (conditional)** | point **unchanged** for pooled; conditional model gives a larger, more correct estimate |
| OR per SD, **SE** | 0.0212 | 0.0505 (cell CRVE) | **SE ×2.4** |
| OR per SD, **95% CI** | [2.16, 2.35] | [2.04, 2.49] (cell CRVE); [2.48, 2.74] (conditional) | pooled CI **≈2× wider** |
| Leakage **AUC 95% CI** | [0.688, 0.708] (item resample) | **[0.674, 0.723]** (cell bootstrap) | **≈2× wider** |
| Exploitability **E 95% CI** | [0.340, 0.382] | **[0.314, 0.410]** (cell bootstrap) | **≈2× wider** |
| Clustered slope p-value | `≈0` (naive) | `3×10⁻⁵⁸` (cell CRVE) | still highly significant |

**Interpretation.**
- The naive analysis **understated the uncertainty by roughly a factor of two**
  (cell level), exactly as theory predicts for positively-correlated clusters.
- The point estimates did **not** change (pooled), so no published number is
  "wrong" in magnitude — the defect was inferential, and it is now corrected
  honestly rather than hidden.
- The conditional logit, which is the *correct* model for this design, gives a
  **larger** odds ratio (2.61 vs 2.25): ignoring within-item competition had been
  *attenuating* the estimated effect, not inflating it.
- Because the synthetic effect is large by construction, significance survives the
  correction. **The methodological point stands independently of that:** on a real
  corpus with a modest effect, the ~2× CI widening is the difference between a
  defensible and an indefensible claim. The manuscript now says exactly this.

The verbosity-differential Wilcoxon test (δ) treats items as independent; its
matched correction is a cell-cluster bootstrap of `δ̄`. The injected effect is so
large (`p ≈ 10⁻²⁵⁵`) that this does not alter the qualitative conclusion, so we
note it here rather than re-reporting it; the machinery
(`clustered_bootstrap_ci`) is in place to apply it to a real corpus.

## 5. Files modified / added

- **Added** `src/stats_robust.py` — `build_option_design`, `logistic_naive`,
  `logistic_cluster_robust`, `conditional_logistic`, `clustered_bootstrap_ci`,
  `compare_all`, plus a CLI that writes `results/stats_robust_synthetic.json`.
- **Modified** `src/analyze.py` — imports `stats_robust`, prints the naive-vs-
  corrected comparison, and embeds it in `results_synthetic.json` under
  `robust_inference`.
- **Modified** `paper/main.tex` — (§3) explains the non-independence and the
  conditional-logit + CRVE + cluster-bootstrap remedy; (§6 Procedure) documents
  clustering-aware inference and the six-cluster caveat; (§7.1) reports the
  corrected AUC CI, the conditional-logit OR `2.61 [2.48, 2.74]`, and the ≈2× CI
  widening under cell clustering.
- **Added** `results/stats_robust_synthetic.json` — machine-readable corrected
  inference.

## 6. How this improves publication readiness

Replaces an anti-conservative, independence-assuming inference (a standard
reviewer objection and a genuine validity threat) with the statistically correct
treatment for a nested "one-of-m" design, **and quantifies the correction's size
transparently**. The change is conservative (it widens intervals, never narrows
them) and reproducible (fixed seeds), and it is exactly the analysis a real-data
version of this study must use.
