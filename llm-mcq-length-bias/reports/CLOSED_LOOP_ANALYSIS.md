# CLOSED_LOOP_ANALYSIS.md — Phase 5: Closed-Loop / Synthetic-Evaluation Audit

## What is the study actually evaluating?

**Self-generated synthetic outputs — not real-world model outputs.**

- `src/synthesize_demo.py` **injects** a length bias by appending semantically
  empty qualifier+filler clauses to the keyed option (strength `b` per
  placeholder model).
- `src/metrics.py` then **measures** length and reports that the keyed option is
  longer.
- `src/analyze.py` reports that the metric "recovers" the injected gradient.

This is a **closed loop**: the same codebase writes the signal and then reads it
back. The dry-run path of the *collection* harness (`collect.py --dry-run`) is
also fed by `synthesize_demo`, so even the harness "test" consumes synthetic
items. **No real model output is evaluated anywhere in the repository.**

This is not, in itself, illegitimate — pipeline verification on controlled ground
truth is standard and valuable. The risk is **rhetorical**: a closed-loop
consistency check can be misread (by an author or a reviewer) as *empirical
validation*. Two failure modes:

1. **Circular validity.** "The metric recovers the bias" is near-tautological when
   the injected bias *is* length and the metric *is* length, with no competing
   content signal. It demonstrates correct implementation, not construct validity.
2. **Implied real-world measurement.** Present-tense descriptions of the harness
   ("elicits MCQs from six assistants") can read as though collection happened.

The manuscript was already far more honest than most on point (2); this phase
tightens the residual wording and adds an explicit statement about point (1).

## Required principle

> The paper must never imply empirical validation where none exists.

Two corollaries enforced here:
- Distinguish **software verification** ("the code computes what it should") from
  **measurement validation** ("the metric captures the real construct"). The paper
  is *about* validity, so this distinction must be airtight.
- Describe unrun capabilities in capability tense ("designed to elicit"), never in
  a tense that asserts they were executed.

## Problematic statements → revised statements (`paper/main.tex`)

| # | Location | Problematic (before) | Revised (after) | Why |
|---|----------|----------------------|-----------------|-----|
| 1 | Abstract (L66) | "a data-collection harness **that elicits** MCQs from six widely used assistants … so the bias can be measured rather than assumed" | "a data-collection harness **designed to elicit** … so the bias can be measured—rather than assumed—**once the harness is run with sanctioned API access (a step not performed in this version)**" | Removes present-tense implication of completed collection. |
| 2 | Intro objectives (L140) | "a … harness **that elicits** items" | "a … harness **that can elicit** items" | Capability tense. |
| 3 | Gap (L234) | "delivered as **validated** tooling" | "delivered as **verified** tooling" | Avoids "validated" (measurement-loaded). |
| 4 | §4 Harness (L319) | "a provider-agnostic harness **that elicits** MCQs from six assistants … through their respective APIs" | "a provider-agnostic harness **designed to elicit** MCQs …" | Capability tense; section already states it was not executed. |
| 5 | Scope (L166) | "exist to **validate** that the metrics behave correctly" | "exist to **verify** that the metrics behave correctly" | Software check, not validation. |
| 6 | §6 Setup (L429) | *(no caveat)* | **Added:** "this is *consistency checking, not measurement validation*: because the synthetic key is lengthened only by appending semantically empty clauses, length is the *sole* injected signal and is uncorrelated with genuine content, so a length-based metric recovering it confirms the implementation is correct but says nothing about whether the metric captures leakage in real items … External validity requires the real corpus." | **Names the circularity explicitly** — the central closed-loop fix. |
| 7 | Discussion (L602) | "an instrument that has been **validated end to end**" | "an instrument that has been **verified end to end (software verification, not measurement validation)**" | Same distinction, at the point of strongest claim. |
| 8 | Limitations (L674) | "The synthetic study **validates** tooling only." | "The synthetic study **verifies** the tooling only." | Consistency. |

## Justification

- **Statements 1–2, 4:** A harness that has never contacted a live endpoint cannot
  be said, in the present indicative, to "elicit" data. Capability framing
  ("designed to / can elicit") states exactly the truth: the tool exists and is
  ready, the data do not.
- **Statements 3, 5, 7, 8:** In assessment science "validation" is a technical term
  about whether a measure reflects its intended construct. Using it for "the code
  runs and returns the injected value" silently borrows that authority. Replacing
  it with "verify/verified" keeps the strong word available for its real meaning
  and removes an unearned implication.
- **Statement 6 (the core addition):** This is the honest heart of the closed-loop
  fix. It tells the reader, in the paper's own voice, that recovering an injected
  length effect with a length metric is *expected by construction* and therefore
  cannot be evidence the metric is valid for real items — where length is entangled
  with specificity, correctness, and difficulty. It points to the real corpus as
  the only route to external validity.

## What remains a closed loop (and is now labeled as such)

- The **metric-recovery demonstration** (§7.2, Fig. 2/3) is still a closed loop by
  necessity; it is now explicitly framed as instrument *sensitivity*
  demonstration, not a finding about real models (see also `CLAIM_AUDIT.md`
  EX-3/GEN-1).
- The **mitigation before/after** (§7.4) is computed on the same synthetic corpus
  with a length-only deterministic rewriter; Phase 3 already added the caveat that
  this measures the length signal, not quality.

Breaking the loop for real requires running `data_collection/` (Phase 6) and
`exploitability.py` (Phase 7) against real model outputs. The manuscript now states
this as the explicit precondition for any empirical claim, with no residual wording
that implies it has already been met.
