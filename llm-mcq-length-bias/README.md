# The Longest-Answer Heuristic

Code and manuscript for a study of **answer-length bias in LLM-generated
multiple-choice questions (MCQs)** — the tendency of large language models, when
asked to author MCQs, to make the *correct* option longer than the distractors,
which lets a test-taker score well above chance by simply "picking the longest
option." We frame this as a measurable threat to assessment validity / academic
integrity, quantify it, and provide algorithms that remove it.

## What's here

```
src/
  metrics.py          Reusable metrics: Longest-Answer Accuracy (LAA),
                      Exploitability E, Verbosity Differential delta,
                      key length-rank distribution, length-leakage AUC,
                      logistic leakage regression, Holm-Bonferroni.
  stats_robust.py     Clustering-aware inference: conditional logit (exact for
                      1-of-m), item/cell cluster-robust SEs, cell cluster bootstrap.
  collect.py          Legacy single-file multi-provider corpus builder (--dry-run).
                      Superseded by data_collection/ (kept for reference).
  synthesize_demo.py  Generates a SYNTHETIC corpus with injectable bias so the
                      pipeline can produce figures before the real corpus exists.
  mitigate.py         Mitigations: length auditor/gate, length-balanced
                      rewriting, length-matched adversarial distractors,
                      option-order/key-rank balancing, and a hardening pipeline.
  exploitability.py   Predictive leakage pipeline: label-free length features,
                      3 baselines (LogReg/RF/GB), group-aware CV, clustered CIs.
                      SELF-TEST-guarded; reportable only on a REAL corpus.
  analyze.py          Runs everything (incl. clustering-aware inference), writes
                      results.json, LaTeX tables, figures.
data_collection/      Modular, tested, reproducible real-collection package
                      (providers, provenance schema, retry/backoff, config-driven,
                      structured logging, experiment tracking). See its README.
reports/              Scientific-review reports (audit, claim alignment, statistics,
                      closed-loop, collection plan, exploitability, citations,
                      title, venue). Start at reports/AUDIT_REPORT.md.
paper/
  main.tex            The manuscript (two-column article class, natbib/bibtex).
  references.bib      Bibliography.
figures/  results/    Generated outputs.
```

## Reproduce the illustrative (synthetic) pipeline

```bash
pip install -r requirements.txt
cd src
python synthesize_demo.py                 # writes data/synthetic_mcq.jsonl
python analyze.py --data ../data/synthetic_mcq.jsonl --tag synthetic \
       --figdir ../figures --outdir ../results
```

## Collect the REAL corpus (the manual step)

Set the relevant API key, then run once per model:

```bash
export ANTHROPIC_API_KEY=...   # or OPENAI_API_KEY / GOOGLE_API_KEY / XAI_API_KEY / ...
python collect.py --provider anthropic --model <model-id> \
       --n-per-cell 30 --out ../data/corpus_claude.jsonl
# ... repeat for openai, google, xai, deepseek, perplexity ...
cat ../data/corpus_*.jsonl > ../data/corpus_all.jsonl
python analyze.py --data ../data/corpus_all.jsonl --tag real \
       --figdir ../figures --outdir ../results
```

Then point `paper/main.tex` at the `*_real` figures/tables instead of the
`*_synthetic` ones.

## IMPORTANT — honesty about the numbers

The figures/tables produced from `synthesize_demo.py` are **illustrative only**
and are labelled as such in the manuscript. They demonstrate that the metrics and
mitigations behave correctly; they are **not** measurements of any real model.
The paper's empirical claims must come from `collect.py` output. The previously
observed "~80% longest-is-correct" figure is a hypothesis to be re-measured, not
an established result.

## Build the paper

```bash
cd paper
pdflatex main && bibtex main && pdflatex main && pdflatex main
```
