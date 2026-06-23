# TITLE_RECOMMENDATIONS.md — Phase 9: Title & Framing Review

## What the old title implied (and why it was a problem)

> *Old:* **"The Longest-Answer Heuristic: Characterizing and Mitigating
> Answer-Length Bias in LLM-Generated Multiple-Choice Questions as a Threat to
> Assessment Integrity."**

| Implied by the title | Supported by the evidence? |
|----------------------|----------------------------|
| Real-world *characterization* of bias in LLM-generated MCQs | ❌ No — all data are synthetic; no real model was measured. |
| A demonstrated *threat to assessment integrity* | ❌ No — no human-subject study; "threat" is asserted, not shown. |
| Large-scale / multi-model empirical analysis | ❌ No — six *placeholder* generators with injected bias. |

The phrase **"as a Threat to Assessment Integrity"** is the sharpest overclaim
(CLAIM_AUDIT AI-1, Class D): it states as fact a real-world consequence the study
does not establish. A second issue: the **cover letter already used a different,
more conservative title** ("Measuring and Mitigating Answer-Length Leakage…"), so
the submission was internally inconsistent.

## Applied change

`paper/main.tex` now reads:

> **"The Longest-Answer Heuristic: Measuring and Mitigating Answer-Length Leakage
> in LLM-Generated Multiple-Choice Questions."**

This (a) drops the unsupported "threat" assertion, (b) uses the paper's defined
construct ("leakage"), and (c) **matches the cover letter**, resolving the
inconsistency. It remains accurate: the paper *does* define measures and
mitigations. Below are five framing-specific options the author can choose among;
the applied title is the "Conservative/Journal" choice.

## Five title options

### 1. Conservative (applied)
**The Longest-Answer Heuristic: Measuring and Mitigating Answer-Length Leakage in
LLM-Generated Multiple-Choice Questions**
- *Strengths:* accurate to the artifact; keeps the memorable hook; matches the
  cover letter; no real-world overclaim.
- *Weaknesses:* "Measuring" could still be read as "measured a real model"; the
  abstract's synthetic disclaimer mitigates this. Does not advertise the
  synthetic/preregistration nature.

### 2. Journal (empirical-leaning, for an education/assessment journal)
**Answer-Length Leakage in LLM-Generated Multiple-Choice Questions: A Measurement
Suite and Generation-Time Mitigations**
- *Strengths:* foregrounds the reusable contribution (suite + mitigations);
  neutral, venue-appropriate; no threat claim.
- *Weaknesses:* drops the catchy "Longest-Answer Heuristic"; still implies the
  phenomenon is established in LLM output (it is hypothesized + synthetically
  validated).

### 3. Conference (CS/NLP venue, punchier)
**Pick the Longest: Auditing and Repairing Answer-Length Leakage in LLM-Written
MCQs**
- *Strengths:* memorable; "auditing and repairing" matches the tool framing;
  fits an NLP/EDM short-paper tone.
- *Weaknesses:* "LLM-Written MCQs" implies real LLM output was analyzed; risks the
  same closed-loop read unless the abstract's caveat is prominent.

### 4. Methods paper (most defensible given current evidence)
**A Measurement-and-Mitigation Toolkit for Answer-Length Leakage in
Machine-Generated MCQs, with Synthetic Validation and a Preregistered Protocol**
- *Strengths:* the *most* honest — names the toolkit, the synthetic validation, and
  the preregistration; essentially reviewer-proof on claim–evidence alignment.
- *Weaknesses:* long; less catchy; signals "no real data yet" up front, which may
  lower perceived impact for some editors.

### 5. Registered report
**Does Answer Length Reveal the Key? A Registered Report on Measuring and
Mitigating Length Leakage in LLM-Generated MCQs**
- *Strengths:* perfectly matched to a Registered-Report track (Stage 1: methods +
  preregistration reviewed before data); turns "no real data yet" from a weakness
  into the format's premise.
- *Weaknesses:* commits to the RR workflow and a target venue that offers it;
  requires the human-subject/real-model plan as the registered Stage-2 study.

## Recommendation

- For **submission now**, keep the applied **Conservative** title (#1) — accurate,
  catchy, consistent with the cover letter.
- If the target is an **empirical** assessment venue, prefer **#4 (Methods)** or
  **#5 (Registered Report)**, which align the *title itself* with the evidence base
  and pre-empt the "where is the real data?" objection (see `VENUE_STRATEGY.md`).
- Whichever is chosen, the manuscript title and the cover-letter title must match.
