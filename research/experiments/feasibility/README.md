# Feasibility: issue-linked AIDev PRs

`feasibility.py` counts AIDev PRs that link an issue with usable text and that have diff rows, per agent and
(for AIDev v3) per task type. Output: `results/feasibility.json`. Needs `pip install duckdb` and the parquet files
listed in the script docstring (about 13 GB for v5 commit details).
