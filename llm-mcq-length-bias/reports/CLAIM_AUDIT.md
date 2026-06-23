# CLAIM_AUDIT.md — Phase 2 Scientific Claim Audit

**Manuscript:** `paper/main.tex` (line numbers refer to that file at audit time)
**Classification key:**

- **A — Supported:** directly backed by evidence currently in the repository.
- **B — Weakly supported:** partially backed; holds for the synthetic corpus or as
  a capability, but is stated in a way that reaches toward real-world generality.
- **C — Unsupported:** no evidence in the repository supports it.
- **D — Overclaim:** evidence exists but is weaker than the claim's strength.

A claim may not exceed the evidence supporting it. Where a claim is B/C/D, a
concrete revision is given. Phases 3 (RQ4), 4 (statistics), 5 (closed-loop), and 9
(title) implement the highest-priority revisions.

Overall: the manuscript is **already heavily caveated** and most claims are A or
defensible B. The audit isolates a small set of genuine problems (one D, a few B/C)
and a large set of A claims that should simply retain their existing "synthetic /
illustrative" qualifiers.

---

## A. Assessment-integrity claims

| ID | Claim (abridged) | Location | Evidence source | Quality | Class | Recommended revision |
|----|------------------|----------|-----------------|---------|-------|----------------------|
| AI-1 | Title: "…Answer-Length Bias in LLM-Generated MCQs **as a Threat to Assessment Integrity**" | Title (L34–37) | Synthetic corpus only | No real-model or human-subject evidence that a threat is realized | **D** | Soften to a *potential/measurable* threat, or move "threat" out of the asserted title. See `TITLE_RECOMMENDATIONS.md`. |
| AI-2 | "When present, this correlation reintroduces a classical item-writing flaw … furnishing test-takers with a … 'pick-the-longest' heuristic that inflates scores" | Abstract (L57–61); Intro (L102–106) | Psychometric literature (Haladyna, Messick, Millman) + synthetic demo | Conditional ("when present"); mechanism grounded in real prior work | **A/B** | Keep; the "when present" hedge is doing the right work. No change required. |
| AI-3 | "every quiz produced this way ships with a built-in cheat code" | Intro (L123) | Hypothetical ("If so") | Rhetorical; conditional | **B** | Acceptable as conditional, but recommend tempering the metaphor in a venue that dislikes rhetoric. Optional. |
| AI-4 | "We position the measurement suite and mitigations as deployable safeguards" | Abstract (L77–78) | Code exists; runs on synthetic data | Deployability untested on real authoring pipelines | **B** | Keep but qualify: "deployable in principle"; note no field deployment yet (already implied by Limitations). |

## B. Exploitability claims

| ID | Claim (abridged) | Location | Evidence source | Quality | Class | Recommended revision |
|----|------------------|----------|-----------------|---------|-------|----------------------|
| EX-1 | "length alone carries a test-taker about 36 % of the way from chance to a perfect cheat" (E=+0.361) | Results (L450–461) | `results_synthetic.json` | True **for the synthetic corpus with injected bias**; not a real-model quantity | **A** (synthetic) | Keep; already preceded by the bold synthetic disclaimer (L445–447). |
| EX-2 | "a length-only classifier achieves a leakage AUC=0.698 … logistic … odds ratio of 2.25 per SD (p≈0)" | Results (L456–460) | `metrics.logistic_length_leakage` | Point estimates fine; **stated p and CI assume option independence** (invalid) | **C** (the inference, not the estimate) | Replace naive p/CI with cluster-robust / conditional-logit values (Phase 4). |
| EX-3 | "the suite is sensitive enough to rank generators by leakage" | Results (L470–473) | Recovery of injected gradient on synthetic data | The instrument recovers a *known* ordering | **A** (as a *methodological* claim) | Keep but frame strictly as instrument validation, not a finding about real models. |
| EX-4 | RQ3 answered: "a longest-option strategy beats chance on leaky corpora and length carries substantial information about the key" | Conclusion (L631–633) | Synthetic corpus | True by construction on synthetic data | **B** | Add "on the synthetic corpus" to the RQ3 answer sentence to avoid a real-world read. |
| EX-5 | Implicit: that the measured AUC/E demonstrates *real* test-taker exploitability | throughout Results | none (no predictive validation on real items; no human subjects) | No external exploitability evidence | **C** | Covered by `EXPLOITABILITY_ANALYSIS.md`: ship pipeline + preregistration; withhold results. |

## C. Item-quality claims  ← primary Phase 3 target

| ID | Claim (abridged) | Location | Evidence source | Quality | Class | Recommended revision |
|----|------------------|----------|-----------------|---------|-------|----------------------|
| IQ-1 | RQ4: "Can generation-time mitigations remove the leak **without degrading item quality**, and by how much (measured before/after)?" | Intro RQ4 (L154–155) | **No item-quality measurement exists anywhere in the repo.** The deterministic mock rewriter appends meaningless filler / trims clauses → it *reduces* meaning. | Zero supporting evidence; the only concrete rewriter degrades quality | **D / C** | Rewrite RQ4 to be about *length characteristics*, not quality. See Phase 3. |
| IQ-2 | "remove the leak without discarding items (RQ4)" | Conclusion (L633) | Pipeline retains all items | True: no items dropped | **A** | Keep ("discarding"), but do **not** let it stand in for a quality claim. |
| IQ-3 | "lightweight mitigations remove the leak without degrading item quality" (any paraphrase) | Abstract/Conclusion framing | none | none | **C** | Ensure no such paraphrase survives (Phase 3 sweep). |
| IQ-4 | Mitigation "produces plausible, content-grounded distractors" (Mitigation C, L364–366) | Prompt text only; deterministic matcher pads text | Claim about *prompted* behavior; the tested path uses a non-semantic mock | **B** | Clarify that plausibility is a *design goal of the prompt*, demonstrated only with a real LLM rewriter (not yet run). |

## D. Generalization claims

| ID | Claim (abridged) | Location | Evidence source | Quality | Class | Recommended revision |
|----|------------------|----------|-----------------|---------|-------|----------------------|
| GEN-1 | RQ2: "How large is the leakage, and does it vary by model, subject, and difficulty?" answered as "the suite resolves model-level differences" | Intro (L150–152); Conclusion (L630) | Synthetic injected gradient | Answers an *instrument* question, not a real-world magnitude | **B** | Keep, but the RQ2 answer must say "the suite can resolve differences (validated on synthetic ground truth)", not imply real magnitudes. |
| GEN-2 | "elicits MCQs from six widely used assistants under an identical, length-neutral prompt" | Abstract (L66–68); Harness (L308–312) | `collect.py` exists; **never executed against live APIs** | Present-tense "elicits" can imply collection happened | **B** | Use capability framing: "is designed to elicit / can elicit"; state plainly it has not been run (already in Limitations L645–648). Phase 5. |
| GEN-3 | "results may not transfer across prompts / models / versions" | Limitations (L656–660) | self-aware | Correctly limits generalization | **A** | Keep — this is a model of good practice. |

## E. Security / threat claims

| ID | Claim (abridged) | Location | Evidence source | Quality | Class | Recommended revision |
|----|------------------|----------|-----------------|---------|-------|----------------------|
| SEC-1 | "This work aims to protect assessment integrity." | Ethics (L714) | Stated intent | Aim, not result | **A** | Keep. |
| SEC-2 | "The metrics and harness could in principle help a student exploit leaky quizzes; we mitigate this by pairing every measurement tool with a remediation tool." | Ethics (L714–718) | Reasonable dual-use framing | Appropriate | **A** | Keep. |
| SEC-3 | Title/abstract framing of a realized integrity *threat* (see AI-1) | Title; Abstract | Synthetic only | Threat not demonstrated in the wild | **D** | Tie to AI-1; soften (Phase 9). |

---

## Summary of required changes (by priority)

1. **IQ-1 / IQ-3 (Class D/C):** remove the "without degrading item quality" claim
   and any paraphrase. → **Phase 3** (`RQ4_FIX_REPORT.md`).
2. **EX-2 (Class C inference):** replace independence-assuming p/CI with
   cluster-robust + conditional-logit values. → **Phase 4**
   (`STATISTICAL_VALIDITY_REPORT.md`).
3. **GEN-2 (Class B):** capability-frame the harness; state it has not been run. →
   **Phase 5** (`CLOSED_LOOP_ANALYSIS.md`).
4. **AI-1 / SEC-3 (Class D):** soften the "threat to assessment integrity" title
   assertion. → **Phase 9** (`TITLE_RECOMMENDATIONS.md`).
5. **EX-5 (Class C):** ship exploitability pipeline + preregistration, results
   withheld. → **Phase 7** (`EXPLOITABILITY_ANALYSIS.md`).

All **A** claims should retain their current synthetic/illustrative qualifiers and
need no change. The manuscript's existing candor means the edit surface is small
and surgical, not a rewrite.
