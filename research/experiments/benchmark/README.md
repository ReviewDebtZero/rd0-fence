# Benchmark: Fence on AIDev, with baselines and PAIChecker labels

Everything here runs on CPU with no API key. The corpus itself (about 1.5 GB of patches) stays out of git;
per-PR scores and summary tables are committed under `results/`.

| Script | Output |
|---|---|
| `build_corpus.py` | `prs.parquet`, `files.parquet`: the 54,058 AIDev v5 PRs with a usable linked issue and >= 90% patched file rows |
| `run_fence.py` | `pr_results.parquet`, `file_results.parquet`: Fence's verdict for every PR and changed file |
| `baselines.py` | `baselines.parquet`: PR size (lines), file count, top-level directories, TF-IDF issue/diff distance |
| `prevalence.py` | [`results/prevalence.md`](results/prevalence.md), `results/prevalence.json` |
| `paichecker.py` | [`results/paichecker.md`](results/paichecker.md), `results/paichecker.json` |

`results/pr_scores.parquet` joins the per-PR Fence outputs and baseline scores (one row per corpus PR).

## Run

```bash
pip install -e "packages/rd0-fence" duckdb pandas pyarrow scikit-learn scipy datasets
hf download hao-li/AIDev --repo-type dataset --local-dir data/aidev
hf download hao-li/AIDev-full --repo-type dataset --local-dir data/aidev_full --include pr_task_type.parquet
cd research/experiments/benchmark
python build_corpus.py --v5 ../../../data/aidev --v3 ../../../data/aidev_full --out ../../../data/fence_bench
python run_fence.py --corpus ../../../data/fence_bench --out ../../../data/fence_bench
python baselines.py --corpus ../../../data/fence_bench
python prevalence.py --corpus ../../../data/fence_bench
# PAIChecker labels: git clone https://github.com/manyiResearch/PAIChecker (labelled_data/); HF splits saved as parquet:
#   SWE-bench/SWE-bench (test), SWE-Gym/SWE-Gym (train), SWE-bench/SWE-bench_Multilingual (test)
python paichecker.py --labels PAIChecker/labelled_data --swebench swebench.parquet \
    --swegym swegym.parquet --multilingual swebml.parquet
```

## What the numbers are and are not

- **Prevalence is Fence's output, not a verified rate.** Fence flags at least one out-of-scope part in 56.6% of
  anchored corpus PRs; 4.4% of PRs (2,361) are *scope unresolvable* (the issue names nothing concrete). How many of
  those flags a reviewer would agree with is unknown until the gold sheet in `../label_audit` is labelled.
- **On PAIChecker's human scope-creep labels, Fence does worse than plain PR size.** AUROC over 3,087 SWE-bench,
  SWE-Gym and SWE-bench Multilingual instances: PR size 0.757, file count 0.673, Fence reach 0.577, TF-IDF 0.577,
  top-level directories 0.510. At the same flag budget (769 instances), PR size has 31.9% precision and Fence
  23.0%. Caveats: these are PR-level labels on human gold patches with tests removed, not agent PRs, and
  PAIChecker's "SC" covers over-reach inside files the issue does name, which Fence's file-level rules cannot see.
- AIDev stores per-commit file rows, so a file's patch is every commit's patch for it joined together; line counts
  can double-count lines rewritten across commits. Copilot PRs are under-represented (many lack patches).
- Task types come from AIDev-full's conventional-commit labels and cover 2,631 corpus PRs.
