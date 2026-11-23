# Experiment design and metric (milestone 1, for review)

## Question
How often, and how much, do coding-agent PRs change things their linked issue did not ask for? Can a cheap,
deterministic checker find those parts well enough to help a reviewer?

## Metric: scope reach
For a PR with diff D and linked issue I, Fence labels every part p of D (a file, or a formatting-only hunk inside an
in-scope file) as in scope or out of scope, and gives a reason.

- **Scope reach** R(PR) = changed lines in out-of-scope parts / all changed lines (generated and vendored files
  excluded). R = 0 means everything traces to the issue.
- **Reach flag**: the PR has at least one out-of-scope part.
- Part categories reported separately: unrelated code, CI/workflow, dependencies/manifests, docs, tests,
  formatting-only.

## Data
1. **Corpus** (prevalence): AIDev v5 pop PRs with usable issue text and diff rows (68,192); main analysis on the
   54,058 where at least 90% of file rows carry a patch, with Copilot coverage reported separately.
2. **Gold sheet** (precision/recall): a stratified sample, about 50 PRs per agent (300 PRs), stratified by size
   bucket. Each changed file and each flagged hunk is labelled `in scope`, `out of scope`, or `support`
   (needed to make the asked change work, such as a test or an import). Two annotators label an overlapping
   subset of 100 PRs; we report Cohen's kappa. Labels are made in a small app like rd0-jinx's label_audit, blind to
   Fence's output.
3. **External labels**: PAIChecker's human labels on SWE-bench Verified (22 SC of 503), SWE-Gym (400 SC of 2,287)
   and SWE-bench Multilingual (33 SC of 300), joined to the gold patches. These are PR-level labels on human PRs,
   so they test transfer, not the agent setting.
4. **Task type**: AIDev v3 labels where PRs overlap; for the rest, the conventional-commit prefix of the title,
   checked against v3 labels on the overlap before use.

## Evaluation
- Part level on the gold sheet: precision, recall and F1 of "out of scope" (main number: precision, since a
  reviewer acts on each flag).
- PR level on the gold sheet and PAIChecker: AUROC and average precision of R for the reach flag.
- Baselines, all tuned on a dev split and tested on a held-out split:
  1. PR size (changed lines).
  2. File count, and number of top-level directories touched.
  3. Text similarity: BM25 / TF-IDF cosine between the issue and each file's path plus changed lines; a file is
     out of scope below a tuned threshold.
  4. Existing tools that run offline (Commitor's offline mode if it installs cleanly). LLM tools (PAIChecker,
     Verdict) only if you approve the API cost; reported apart from the default no-key path.
- Ablations: path rules only; plus code names; plus lexical terms; plus companion rules (tests, wiring, lockfiles).

## Empirical paper analyses
- RQ1: prevalence of scope reach by agent (R distribution, reach-flag rate), with gold-set precision attached.
- RQ2: by task type and by category of out-of-scope part.
- RQ3: association with outcomes (merged or not, review comments, later reverts), controlling for PR size and repo.
All rates are reported with confidence intervals and corrected by measured precision where it matters.

## Threats
Issue text can be vague (Fence then reports "scope unknown" and only judges CI, dependency and formatting parts);
some extras are welcome (maintainers asked in comments, not in the issue); AIDev diff rows are per commit.
