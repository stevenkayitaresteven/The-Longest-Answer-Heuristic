# Cover Letter — template

> **How to use this file.** Replace every `[[BRACKETED]]` placeholder. The
> letter must name a *specific* journal, so choose the venue before sending.
> Keep it to one page. Delete this note block before submitting.

---

[[YOUR NAME]]
[[DEPARTMENT / PROGRAM]], [[INSTITUTION]]
[[EMAIL]]  ·  ORCID: [[0000-0000-0000-0000]]

[[DATE]]

To the Editors of *[[JOURNAL NAME]]*,

Dear Editor-in-Chief,

I am writing to submit our manuscript, **"The Longest-Answer Heuristic: Measuring
and Mitigating Answer-Length Leakage in LLM-Generated Multiple-Choice Questions,"**
for consideration as a *[[ARTICLE TYPE — e.g. research article / methods paper /
short communication]]* in *[[JOURNAL NAME]]*.

Large language models are now routinely used by educators and students to author
multiple-choice questions at scale. Our manuscript identifies and formalizes an
underexamined failure mode in this practice: a systematic correlation between the
length of an answer option and its probability of being keyed correct. When this
correlation is present, it reintroduces a classical item-writing flaw — "the
longest option is correct" — at machine scale, handing test-takers a
construct-irrelevant "pick-the-longest" heuristic that inflates scores without
measuring knowledge. We treat this as a measurable threat to assessment validity
and academic integrity.

The manuscript makes four contributions: (1) a formal definition of *answer-length
leakage* together with a reusable, model-agnostic measurement suite (Longest-Answer
Accuracy, an Exploitability index, a verbosity differential, and a length-only
leakage AUC); (2) an open, provider-agnostic data-collection harness that elicits
MCQs from six widely used assistants under an identical, length-neutral prompt;
(3) a generation-time mitigation toolkit with a measured before/after protocol; and
(4) a fully reproducible analysis pipeline.

In the interest of full transparency, we note that we did not have sanctioned API
access to all six commercial systems at the time of submission. The quantitative
results in the present version are therefore generated from a clearly labeled
*synthetic* corpus that exercises the entire pipeline end to end; they demonstrate
that the metrics and mitigations behave as designed and are explicitly *not*
presented as measurements of any real model. We include a preregistered protocol
for the real-model and human-subject studies needed to confirm the effect in the
wild. We believe the measurement suite and deployable mitigations are of immediate
value to the [[readership / scope]] of *[[JOURNAL NAME]]* on their own merits, and
we welcome the editors' guidance on whether the synthetic-pipeline framing fits the
journal's scope or whether real-model data should accompany a revised submission.

This work is original, has not been published elsewhere, and is not under
consideration by another journal. All authors have approved the manuscript and
agree to its submission. We have no conflicts of interest to declare (see the
enclosed disclosure statements). All code and the synthetic corpus are publicly
available; the data-availability statement is enclosed.

We suggest the following experts as potential reviewers, none of whom have a
conflict of interest with the authors: [[REVIEWER 1, affiliation, email]];
[[REVIEWER 2, affiliation, email]]; [[REVIEWER 3, affiliation, email]].

Thank you for considering our submission. I am happy to provide any further
information.

Sincerely,

[[YOUR NAME]], on behalf of all authors
[[INSTITUTION]]
