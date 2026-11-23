# Claims ledger

Every number in the paper (`short/`, and the deferred `tooldemo/` draft) comes from `generated/numbers.tex` and the `generated/tab_*.tex` tables, which
`scripts/make_paper_numbers.py` builds from the files below. No number is typed into the LaTeX by hand.
All prevalence numbers are Fence's own flags; no human-label result is reported (the gold sheet is unlabelled, and
the gold-sheet table in the paper is an explicit placeholder with no values).

| Claim | Source |
|---|---|
| Corpus size, anchored PRs, scope unresolvable, any/high flag rates, mean/median reach, categories, per-agent and per-task rates | `research/experiments/benchmark/results/prevalence.json` (`prevalence.py`) |
| 7,149 repositories, 2,631 PRs with a task type | `results/composition.json` → `corpus` (`composition.py`) |
| Median files, share over 16 files, file-count-standardized flag rates, missing-patch share, Copilot's most-flagged files, merged vs unmerged (raw and standardized) | `results/composition.json` (`composition.py`) |
| PAIChecker AUROCs, precision/recall at Fence's flag budget | `results/paichecker.json` (`paichecker.py`) |
| Fence + size cross-validated AUROC, paired bootstrap gain, size-tercile AUROCs | `results/combo.json` (`combo.py`) |
| Latency (median / p90 / p99 ms per PR on 2,000 PRs) | `results/latency.json` (`latency.py`) |
| Gold sheet: 300 PRs, 1,471 files, 19 Fence-unresolvable | `research/experiments/label_audit/human/sample_summary.json` |
| Revert causes 22.33% / 22.13% / 17.71% of 33,580 agent PRs | Oukhay et al., MSR 2026, doi 10.1145/3793302.3793587 |

Rebuild: `make -C research/paper PY=python` (needs matplotlib and a TeX Live with latexmk).
