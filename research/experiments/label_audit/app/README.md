# Labeling app (300 agent PRs, per-file scope labels)

One PR at a time: the linked issue, the PR title and every changed file's patch (long patches are truncated; links
open the live PR and issue). Issue, title and patch text is HTML-escaped before rendering. Annotators do not see
the agent or Fence's verdicts.

## Run

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:7860. Each annotator enters a different name (e.g. `A` and `B`); answers are appended to
`answers/<name>.jsonl` as `{id, unresolvable, out_of_scope, cant_tell, note}`. Unticked files count as in scope.
Reopening the app resumes at the first unlabelled PR, and re-saving a PR appends a new line; the last save wins.
Never commit `answers/` (it is git-ignored) or show annotators `../human/key_do_not_open.csv`.

## Score

From `research/experiments/label_audit/`:

```bash
python human/agreement.py app/answers/a.jsonl app/answers/b.jsonl
```

`agreement.py` accepts `.jsonl` answers and filled copies of `human/gold_sheet.csv` interchangeably and writes
`human/agreement.json`: per annotator, PRs labelled, how many are scope unresolvable, file label counts, Fence and
baseline precision/recall/AUROC; pairwise Cohen's kappa on file labels and on the unresolvable flag.

`../human/make_sheet.py` regenerates `tasks.jsonl`; the committed `tasks.jsonl` means the app runs without the
benchmark data.
