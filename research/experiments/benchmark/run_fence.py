"""Run Fence (default settings, no network) on every corpus PR and write per-PR and per-file results.

Usage: python run_fence.py --corpus data/fence_bench --out data/fence_bench [--workers 8]
Writes pr_results.parquet and file_results.parquet under --out.
"""

from __future__ import annotations

import argparse
import json
import posixpath
from multiprocessing import Pool
from pathlib import Path

import pandas as pd
from rd0_fence import Issue, check
from rd0_fence.diff import files_from_patches

CATEGORY = {
    "code": "unrelated code",
    "config": "unrelated code",
    "test": "tests",
    "docs": "docs",
    "ci": "ci",
    "manifest": "dependencies",
    "lockfile": "dependencies",
}


def category(part) -> str:
    if part.hunk or part.reason.startswith("formatting-only"):
        return "formatting"
    return CATEGORY.get(part.kind, part.kind)


def top_dir(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "."


def run_one(args):
    pr, files = args
    issues = [Issue.from_text(i.get("title") or "", i.get("body") or "", i.get("number")) for i in pr["issues"]]
    fcs = files_from_patches(files)
    rep = check(Issue.merge(issues), fcs)
    flagged = rep.flagged
    cats = {}
    for p in flagged:
        cats[category(p)] = cats.get(category(p), 0) + p.lines
    row = {
        "pr_id": pr["pr_id"],
        "anchored": rep.anchored,
        "total_lines": rep.total_lines,
        "out_lines": rep.out_lines,
        "reach": rep.out_fraction,
        "n_flagged": len(flagged),
        "n_flagged_high": sum(p.severity == "high" for p in flagged),
        "n_files": len(fcs),
        "n_top_dirs": len({top_dir(f.path) for f in fcs}),
        "size_lines": int(sum((f.get("additions") or 0) + (f.get("deletions") or 0) for f in files)),
        "flag_categories": json.dumps(cats, sort_keys=True),
    }
    parts = [
        {
            "pr_id": pr["pr_id"],
            "path": p.path,
            "kind": p.kind,
            "dir": posixpath.dirname(p.path),
            "lines": p.lines,
            "in_scope": p.in_scope,
            "hunk": p.hunk,
            "severity": p.severity,
            "category": None if p.in_scope else category(p),
            "reason": p.reason,
        }
        for p in rep.parts
    ]
    return row, parts


def tasks(corpus: Path):
    prs = pd.read_parquet(corpus / "prs.parquet", columns=["pr_id", "issues"])
    files = pd.read_parquet(
        corpus / "files.parquet", columns=["pr_id", "filename", "status", "additions", "deletions", "patch"]
    )
    by_pr = {k: g.to_dict("records") for k, g in files.groupby("pr_id", sort=False)}
    del files
    for pr in prs.itertuples(index=False):
        items = by_pr.get(pr.pr_id, [])
        yield {"pr_id": pr.pr_id, "issues": json.loads(pr.issues)}, items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    rows, parts = [], []
    with Pool(a.workers) as pool:
        for i, (r, ps) in enumerate(pool.imap_unordered(run_one, tasks(Path(a.corpus)), chunksize=64)):
            rows.append(r)
            parts.extend(ps)
            if i % 5000 == 0:
                print(i, flush=True)
    out = Path(a.out)
    pd.DataFrame(rows).to_parquet(out / "pr_results.parquet", index=False)
    pd.DataFrame(parts).to_parquet(out / "file_results.parquet", index=False)
    print(f"prs={len(rows)} parts={len(parts)}")


if __name__ == "__main__":
    main()
