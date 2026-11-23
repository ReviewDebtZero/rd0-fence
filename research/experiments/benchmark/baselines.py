"""Compute the four PR-level baseline scores for every corpus PR (higher = more likely to exceed scope).

size_lines: added + deleted lines; n_files: files changed; n_top_dirs: distinct top-level directories;
tfidf_dist: 1 - TF-IDF cosine similarity between the linked issue text and the diff (paths + changed lines).

Usage: python baselines.py --corpus data/fence_bench   (needs pr_results.parquet from run_fence.py)
Writes baselines.parquet (pr_id + the four scores).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from common import diff_text, issue_text, tfidf_similarity


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    a = ap.parse_args()
    c = Path(a.corpus)
    prs = pd.read_parquet(c / "prs.parquet", columns=["pr_id", "issues"])
    res = pd.read_parquet(c / "pr_results.parquet", columns=["pr_id", "size_lines", "n_files", "n_top_dirs"])
    files = pd.read_parquet(c / "files.parquet", columns=["pr_id", "filename", "patch"])
    files["t"] = [diff_text(f, p) for f, p in zip(files.filename, files.patch)]
    diffs = files.groupby("pr_id", sort=False)["t"].agg("\n".join)
    del files
    prs["issue_text"] = [issue_text(json.loads(x)) for x in prs.issues]
    prs["diff_text"] = prs.pr_id.map(diffs).fillna("")
    prs["tfidf_dist"] = 1 - tfidf_similarity(prs.issue_text.tolist(), prs.diff_text.tolist())
    out = res.merge(prs[["pr_id", "tfidf_dist"]], on="pr_id")
    out.to_parquet(c / "baselines.parquet", index=False)
    print(out.describe().T.to_string())


if __name__ == "__main__":
    main()
