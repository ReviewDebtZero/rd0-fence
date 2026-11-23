"""Time Fence on a random sample of corpus PRs (one process, CPU only), as a GitHub runner would run it.

Usage: python latency.py --corpus data/fence_bench [--n 2000]
Writes results/latency.json.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from rd0_fence import Issue, check
from rd0_fence.diff import files_from_patches

HERE = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    corpus = Path(a.corpus)
    prs = pd.read_parquet(corpus / "prs.parquet", columns=["pr_id", "issues"]).sample(a.n, random_state=0)
    files = pd.read_parquet(
        corpus / "files.parquet",
        columns=["pr_id", "filename", "status", "additions", "deletions", "patch"],
        filters=[("pr_id", "in", prs.pr_id.tolist())],
    )
    by_pr = {k: g.to_dict("records") for k, g in files.groupby("pr_id")}
    ms, n_files = [], []
    for pr in prs.itertuples(index=False):
        items = by_pr.get(pr.pr_id, [])
        t = time.perf_counter()
        issues = [
            Issue.from_text(i.get("title") or "", i.get("body") or "", i.get("number")) for i in json.loads(pr.issues)
        ]
        check(Issue.merge(issues), files_from_patches(items))
        ms.append(1000 * (time.perf_counter() - t))
        n_files.append(len(items))
    ms = np.array(ms)
    res = {
        "prs": a.n,
        "median_ms": round(float(np.median(ms)), 1),
        "p90_ms": round(float(np.percentile(ms, 90)), 1),
        "p99_ms": round(float(np.percentile(ms, 99)), 1),
        "max_ms": round(float(ms.max()), 1),
        "median_files": float(np.median(n_files)),
        "cpu": platform.processor() or platform.machine(),
        "python": platform.python_version(),
    }
    Path(a.out, "latency.json").write_text(json.dumps(res, indent=1) + "\n")
    print(res)


if __name__ == "__main__":
    main()
