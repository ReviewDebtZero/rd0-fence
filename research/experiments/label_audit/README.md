# Gold sheet: per-file scope labels for 300 agent PRs

Humans label which changed files go beyond what the linked issue asked for. The sheet is drawn from the
[benchmark corpus](../benchmark/): 50 PRs per agent (Claude Code, Copilot, Codex, Cursor, Devin, Jules), 1,471 files,
simple random within each agent among PRs with 1-20 files and at most 3,000 changed lines (seed 13; never
conditioned on Fence's output). Counts are in [`human/sample_summary.json`](human/sample_summary.json).

Labels per file: **in scope**, **out of scope**, **can't tell**. Per PR: **scope unresolvable** when the issue is
too vague to say what is in scope. Fence marks 19 of the 300 PRs unresolvable; the human count is reported only
after annotators finish.

- [`app/`](app/): Gradio labeling app (one PR at a time, resumable).
- [`human/gold_sheet.csv`](human/gold_sheet.csv): the same rows as a spreadsheet, for annotators who prefer one.
- `human/key_do_not_open.csv`: Fence's per-file verdicts and baseline scores. Annotators must not open it.
- [`human/agreement.py`](human/agreement.py): scores answers once they exist.
- [`human/make_sheet.py`](human/make_sheet.py): regenerates the sheet from the corpus.

No human labels, agreement or precision numbers exist yet.
