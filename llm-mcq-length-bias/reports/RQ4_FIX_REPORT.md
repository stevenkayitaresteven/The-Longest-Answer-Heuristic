# RQ4_FIX_REPORT.md — Phase 3: Removing the Item-Quality Overclaim

## The problem

RQ4 (and its conclusion answer) asked whether mitigations remove the leak
**"without degrading item quality."** No item-quality measurement exists anywhere
in the repository. Worse, the only concrete rewriter exercised in the before/after
experiment — the deterministic `mock_llm_resize` / `mock_llm_rewrite` in
`src/mitigate.py` — neutralizes length by **trimming trailing clauses or appending
semantically empty filler** (`"... furthermore this option is stated in full and
precise detail for clarity ..."`). That operation *reduces* semantic quality by
construction. A claim that mitigation preserves quality therefore not only lacked
supporting evidence; the demonstrated mechanism provides mild evidence *against*
it.

**Scientific risk addressed:** claim–evidence misalignment (an overclaim, Class D
in `CLAIM_AUDIT.md`, item IQ-1/IQ-3). A claim may not exceed the evidence
supporting it. This is the single most clear-cut integrity defect in the
manuscript and a likely desk-reject trigger for a careful reviewer.

**Technique used:** claim–evidence alignment. Every modification narrows a claim
until it is fully covered by evidence in the repository, and explicitly relocates
the unmeasured part to future work.

## Where the claim appeared (located via full-text search of `paper/main.tex`)

| Line(s) | Original text | Disposition |
|---------|---------------|-------------|
| 154–155 | RQ4: "remove the leak **without degrading item quality**, and by how much (measured before/after)?" | **Rewritten** (length, not quality) |
| 629–636 | Conclusion: "lightweight mitigations remove the leak without discarding items (RQ4)" | **Rewritten** + explicit "did not evaluate quality" |
| 98, 195, 211 | "high-quality MCQs", "quality-control gaps", "independent of quality" | **Left unchanged** — these describe the *literature*, not our mitigation, and are correctly used. |

A repository-wide search confirmed there were **no other** occurrences of a
quality-preservation claim (abstract, mitigation section, and results §4.4 do not
assert quality preservation).

## Changes made (file: `paper/main.tex`)

1. **RQ4 restatement (L154–155).** Now reads (paraphrased): "Can generation-time
   mitigations remove the *length signal* — measured before/after on the
   option-length metrics — and by how much? (We evaluate *option-length
   characteristics*, not pedagogical item quality; assessing quality remains future
   work.)" This adopts two of the acceptable wordings prescribed for this fix
   ("option-length characteristics rather than pedagogical quality" and "assessing
   item quality remains future work").

2. **Conclusion RQ4 answer (L629–636).** Bounded to the synthetic corpus and
   extended with: "We did *not* evaluate pedagogical item quality, and the
   deterministic rewriter used in the demonstration manipulates length only;
   whether a length-balancing rewrite preserves item quality is left to future
   work."

3. **New Limitations bullet (§Limitations).** Added "**Item quality is not
   evaluated.**" — states plainly that the deterministic rewriter is *not* a
   meaning-preserving editor and that an explicit quality assessment (expert
   review, readability, answerability) plus a real LLM rewriter are prerequisites
   for any quality-preservation claim.

4. **Results §4.4 caveat.** Appended: "These before/after numbers quantify the
   *length* signal only; they are not a measure of item quality, which we do not
   evaluate here."

## Why these changes improve publication readiness

- **Eliminates the overclaim** that a careful reviewer would flag as evidence
  fabrication-by-implication, replacing it with a precise statement of what was and
  was not measured.
- **Preserves all genuinely supported claims** — the length-signal reduction
  (E +0.36→−0.06, leaky 71%→3%) is real on the synthetic corpus and is retained
  verbatim; only the *quality* gloss is removed.
- **Converts a liability into a clearly scoped future-work item**, which reviewers
  read as methodological maturity rather than as a gap being hidden.
- **Aligns the manuscript with its own honest framing** elsewhere (the synthetic
  disclaimer, the limitations list), removing an internal inconsistency.

## Residual risk / what is still owed

The mitigation toolkit's *content-grounded* path (length-matched adversarial
distractors via a real LLM) is described but only the deterministic stand-in is
executed. Substantiating "mitigation preserves quality" empirically requires (a)
running a real LLM rewriter and (b) a quality instrument. Both are now explicitly
deferred to future work rather than implied as done. No code change can manufacture
this evidence; the honest move is the wording fix above.
