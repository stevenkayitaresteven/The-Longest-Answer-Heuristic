# CITATION_AUDIT.md — Phase 8: Reference Verification

**File audited:** `paper/references.bib` (18 entries).
**Method:** each entry checked for existence and metadata correctness via web
search, the alphaXiv paper service, and (for canonical works) established record.
**Headline finding:** **no hallucinated references.** All 18 cited works exist.
The only defects were **incomplete metadata** on four recent entries, now
completed and documented below. Per the audit rule, **no citation was silently
modified** — every change is listed.

## Verification status (all 18)

| Key | Exists? | Authors | Year | Venue | Title | Verification | Action |
|-----|:------:|:------:|:----:|:-----:|:-----:|--------------|--------|
| haladyna1989taxonomy | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (AME 2(1):37–50) | none |
| haladyna2002review | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (AME 15(3):309–334) | none |
| tarrant2006frequency | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (Nurse Educ Pract 6(6)) | none |
| downing2005effects | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (Adv Health Sci Educ 10(2)) | none |
| rodriguez2005three | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (EM:IP 24(2)) | none |
| messick1989validity | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (Educational Measurement, 3rd ed.) | none |
| millman1965testwiseness | ✅ | ✅ | ✅ | ✅ | ✅ | canonical (EPM 25(3)) | none |
| kurdi2020systematic | ✅ | ✅ | ✅ | ✅ | ✅ | IJAIED 30(1):121–204 | none |
| qiu2020automatic | ✅ | ✅ | ✅ | ✅ | ✅ | COLING 2020 | none |
| zheng2023judging | ✅ | ✅ | ✅ | ✅ | ✅ | MT-Bench, NeurIPS 2023 | none |
| saito2023verbosity | ✅ | ✅ | ✅ | ✅ | ✅ | **web-verified** authors; arXiv:2310.10076 | none |
| zheng2024robust | ✅ | ✅ | ✅ | ✅ | ✅ | ICLR 2024 | none |
| wang2024lookatthetext | ✅ | ✅ | ✅ | ✅ | ✅ | arXiv:2404.08382 | none |
| awalurahman2024distractor | ✅ | ✅ | ✅ | ✅ | ✅ | **web-verified**; PeerJ CS 10:e2441 | **added DOI** 10.7717/peerj-cs.2441 |
| an2026orchestrating | ✅ | ✅ | ✅ | ✅ | ✅ | **web/alphaXiv-verified**: Yuan An, arXiv:2602.18891 | none (author already correct) |
| benchmarker2026 | ✅ | ⚠️→✅ | ✅ | ✅ | ✅ | **alphaXiv-verified**: arXiv:2602.06221 | **added 9 authors + eprint** |
| frontiers2026automation | ✅ | ⚠️→✅ | ✅ | ✅ | ✅ | **web-verified**: DOI 10.3389/fcomp.2026.1831250 | **added authors + DOI; `@misc`→`@article`** |
| comparativeMCQ2025 | ✅ | ⚠️→✅ | ✅ | ✅ | ✅ | **web-verified**: DOI 10.1016/j.caeai.2025.100440 | **added authors, vol, pages, DOI; `@misc`→`@article`** |

(✅ = correct as cited; ⚠️→✅ = was missing, now completed.)

## Corrections made (every change documented)

1. **`benchmarker2026`** — added the verified author list (Balepur, Rajasekaran,
   Oh, Xie, Desai, Rudinger, Choi, Gupta, Moore — UMD/NYU/Scale AI/George Mason,
   confirmed via alphaXiv) and `eprint = {2602.06221}` / `archivePrefix = {arXiv}`.
   Title, year, and arXiv id were already correct.

2. **`frontiers2026automation`** — converted `@misc`→`@article`; added authors
   (Menze, D.; Radović, S.; Seidel, N. — *initials as verified from the publisher
   listing*) and `doi = {10.3389/fcomp.2026.1831250}`. Note: only initials were
   confirmable from search; the submitter should expand to full first names from
   the published PDF before final submission.

3. **`comparativeMCQ2025`** — converted `@misc`→`@article`; added authors
   (Azzi, A.; Erdős, F.; Németh, R.; Varadarajan, V.; Afrifa, S. — *initials as
   verified*), `volume = {9}`, `pages = {100440}`, and
   `doi = {10.1016/j.caeai.2025.100440}`.

4. **`awalurahman2024distractor`** — added `doi = {10.7717/peerj-cs.2441}`.

All four edits were verified to compile: `pdflatex → bibtex → pdflatex ×2` runs
clean with **no undefined citations** and all 18 `\bibitem`s resolved.

## Flags and residual notes

- **No missing references** for the claims as written — every in-text `\citep`
  resolves.
- **No hallucinated references** — every entry corresponds to a real, locatable
  work.
- **Citation-context nuance (not a metadata error):** at §2 (Related Work),
  `an2026orchestrating` is cited alongside `frontiers2026automation` to support
  "AI-assisted authoring can *increase the rate of item-writing flaws through
  automation bias.*" The An (2026) pilot study is about MCQ-generation *quality
  gaps* versus expert items, not specifically about automation bias raising flaw
  rates. `frontiers2026automation` is the correct support for that exact clause;
  the An citation is better read as support for "LLM MCQ generation has measurable
  quality gaps." Consider splitting the two citations across the two sub-claims.
- **Initials vs full names:** for `frontiers2026automation` and
  `comparativeMCQ2025`, author *initials* were the most that public search
  reliably returned; they are recorded as such rather than guessed full names
  (no fabrication). Expand from the source PDFs before camera-ready.
- **Optional polish (not done, to avoid introducing errors):** DOIs for the
  canonical pre-2010 works could be added but are not required for
  identification; they should be transcribed from the publisher, not generated.

## How this improves publication readiness

Removes the most basic reviewer/editor red flag (incomplete or fabricated
references), confirms the literature base is genuine and on-point — including the
directly competing 2026 BenchMarker and Frontiers automation-bias studies — and
leaves a transparent record so any further metadata completion is a transcription
task, not a re-verification.
