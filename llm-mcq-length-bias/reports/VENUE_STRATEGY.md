# VENUE_STRATEGY.md — Phase 10: Venue Strategy

## Evidence base (after Phases 1–9)

**Have:** a formal construct (answer-length leakage) + reusable metric suite;
clustering-aware, statistically valid inference; a generation-time mitigation
toolkit; a modular, tested real-collection package; an exploitability ML pipeline +
preregistered protocol; verified citations; honest, claim-aligned framing; full
reproducibility.

**Lack:** any real-model corpus; any human-subject exploitability data; any
item-quality measurement. Every quantitative number is synthetic and labeled as
such.

This profile is a **strong methods/tools contribution with a preregistered
empirical plan**, not an empirical findings paper. Venue choice should match that.

## Options

### Option A — Empirical journal (education/assessment or CS:AI in education)
*e.g. Computers & Education: AI; British J. Educational Technology; IEEE TLT.*
- **Probability of acceptance (as-is): ~10–20%.** The field now has *real* recent
  results (BenchMarker; the Frontiers automation-bias study) that an empirical
  venue will benchmark against; a synthetic-only paper invites "where is the real
  data?"
- **Remaining requirements:** run `data_collection/` against ≥2–3 real models;
  report leakage with the clustering-aware stats; ideally the human-subject
  exploitability study.
- **Risks:** desk-reject for "no empirical contribution"; being scooped/over­shadowed
  by BenchMarker-style work.
- **Expected reviewer objections:** "synthetic data cannot support claims about
  LLMs"; "exploitability is asserted, not measured"; "no quality evaluation of
  mitigations." (Phases 3–7 pre-empt the *framing* objections but not the *data*
  one.)

### Option B — Methods paper (measurement/methodology venue)
*e.g. Behavior Research Methods; a measurement-methods or EDM methods track.*
- **Probability (as-is): ~45–60%.** The contribution *is* the method; the metric
  suite + clustering-aware inference + mitigation algorithms stand on their own.
- **Remaining requirements:** sharpen the metric-validation story (sensitivity on
  controlled ground truth is fine *as a method demonstration*); make the
  conditional-logit/CRVE treatment a named methodological feature.
- **Risks:** "method without a real application" — mitigated by the synthetic
  validation being explicitly a *method* demonstration, plus the collection package.
- **Expected reviewer objections:** "show the metric on at least one real corpus";
  "how do thresholds generalize?" Modest, addressable.

### Option C — Tool / artifact paper
*e.g. JOSS; an artifact/demo track (ACL/EMNLP System Demos, EDM tools).*
- **Probability (as-is): ~55–70%.** The repository is reproducible, tested
  (18 passing tests), documented, and modular — exactly what artifact tracks reward.
- **Remaining requirements:** packaging polish (pip-installable, CI, usage docs);
  JOSS wants a clear statement of need + tests + docs (largely met).
- **Risks:** tool venues value *use*; a tool never run on real data is weaker.
  Pairing with even a small real run strengthens it greatly.
- **Expected reviewer objections:** "demonstrate on real provider output"; "add CI
  and an install path." Low-effort to address.

### Option D — Registered Report
*e.g. an RR track at an education/assessment or metascience venue.*
- **Probability (Stage 1, as-is): ~40–55%.** The preregistered protocol
  (`EXPLOITABILITY_ANALYSIS.md`) + collection harness + valid statistics are
  precisely what Stage-1 RR review evaluates; "no data yet" is the *expected* state.
- **Remaining requirements:** pick an RR-offering venue; convert the protocol to its
  Stage-1 template; add a power analysis and the human-subject/IRB plan.
- **Risks:** commits to the RR timeline and to running the study; fewer venues offer
  RRs in this area.
- **Expected reviewer objections:** "specify power and stopping rules"; "justify the
  model/subject grid." The protocol already anticipates these.

## Recommendation

1. **Primary: Option D (Registered Report)** if an appropriate track is available —
   it converts the central weakness (no real data) into the format's premise, and
   the project is unusually well-suited (valid stats + harness + preregistration
   already in hand).
2. **Otherwise / in parallel: Option C (Tool/artifact paper)** for the software
   (highest acceptance odds now), and/or **Option B (Methods paper)** for the metric
   suite + clustering-aware inference.
3. **Defer Option A (empirical journal)** until `data_collection/` has been run on
   real models and analyzed with the clustering-aware pipeline (and, ideally, the
   human-subject study completed). At that point the title can move to the
   empirical variant (`TITLE_RECOMMENDATIONS.md` #2) and the synthetic results
   become a validation appendix.

## Cross-cutting requirements before *any* submission (now satisfied)

- Claim–evidence alignment (Phases 2–3, 5, 9): ✅
- Statistically valid inference (Phase 4): ✅
- Honest data-availability + disclosures: ✅ (already present)
- Verified references (Phase 8): ✅
- Reproducible, tested artifact (Phases 6–7): ✅

The single remaining gate for the *empirical* path is **data collection**, for
which the infrastructure and protocol are now in place.
