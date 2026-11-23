"""Draw the Fence gold sheet: ~300 AIDev corpus PRs, 50 per agent, labelled per file by humans.

Eligible PRs: in the benchmark corpus, 1-20 changed files and at most 3,000 changed lines (so one PR fits on a
screen); sampling is simple random within each agent (seed 13), never conditioned on Fence's output.

Usage (from research/experiments/label_audit/):
    python human/make_sheet.py --corpus data/fence_bench
Writes:
    app/tasks.jsonl            what annotators see (issue, PR title, per-file patches; no agent, no Fence output)
    human/gold_sheet.csv       the same files as a spreadsheet, one row per (PR, file), label columns blank
    human/key_do_not_open.csv  Fence's per-file verdicts and baseline scores, for scoring only
    human/sample_summary.json  eligibility and sample counts
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmark"))
from common import diff_text, issue_text, tfidf_similarity  # noqa: E402

PER_AGENT = 50
MAX_FILES = 20
MAX_LINES = 3000
MAX_PATCH_LINES = 250
MAX_ISSUE_CHARS = 8000
SEED = 13


def truncate(text: str, n: int) -> str:
    lines = (text or "").splitlines()
    return "\n".join(lines[:n]) + (f"\n... ({len(lines) - n} more lines)" if len(lines) > n else "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    a = ap.parse_args()
    c = Path(a.corpus)
    prs = pd.read_parquet(c / "prs.parquet", columns=["pr_id", "agent", "html_url", "repo_url", "pr_title", "issues"])
    res = pd.read_parquet(c / "pr_results.parquet")
    base = pd.read_parquet(c / "baselines.parquet", columns=["pr_id", "tfidf_dist"])
    df = prs.merge(res, on="pr_id").merge(base, on="pr_id")
    ok = df[(df.n_files >= 1) & (df.n_files <= MAX_FILES) & (df.size_lines <= MAX_LINES)]
    rng = np.random.default_rng(SEED)
    picks = []
    for _agent, g in sorted(ok.groupby("agent")):
        g = g.sort_values("pr_id")
        picks.append(g.iloc[np.sort(rng.choice(len(g), min(PER_AGENT, len(g)), replace=False))])
    s = pd.concat(picks).sample(frac=1, random_state=SEED).reset_index(drop=True)
    ids = set(s.pr_id)
    files = pd.read_parquet(c / "files.parquet", filters=[("pr_id", "in", list(ids))])
    parts = pd.read_parquet(c / "file_results.parquet", filters=[("pr_id", "in", list(ids))])
    files = files.sort_values(["pr_id", "filename"])
    s["issues_list"] = s.issues.map(json.loads)

    tasks, sheet = [], []
    for pr in s.itertuples(index=False):
        fs = files[files.pr_id == pr.pr_id]
        iss = pr.issues_list
        issue_md = "\n\n---\n\n".join(
            f"#### Issue #{i.get('number')}: {i.get('title') or ''}\n\n{(i.get('body') or '')[:MAX_ISSUE_CHARS]}"
            for i in iss
        )
        tasks.append(
            {
                "id": str(pr.pr_id),
                "repo": pr.repo_url.removeprefix("https://api.github.com/repos/"),
                "pr_url": pr.html_url,
                "issue_urls": [i.get("url") for i in iss],
                "pr_title": pr.pr_title,
                "issue": issue_md,
                "files": [
                    {
                        "path": f.filename,
                        "status": f.status,
                        "additions": int(f.additions or 0),
                        "deletions": int(f.deletions or 0),
                        "patch": truncate(f.patch, MAX_PATCH_LINES),
                    }
                    for f in fs.itertuples(index=False)
                ],
            }
        )
        for f in fs.itertuples(index=False):
            sheet.append(
                {
                    "id": f"{pr.pr_id}::{f.filename}",
                    "pr_id": pr.pr_id,
                    "pr_url": pr.html_url,
                    "issue_url": iss[0].get("url"),
                    "path": f.filename,
                    "status": f.status,
                    "additions": int(f.additions or 0),
                    "deletions": int(f.deletions or 0),
                    "label": "",
                    "pr_scope_unresolvable": "",
                    "note": "",
                }
            )

    sheet = pd.DataFrame(sheet)
    out_paths = parts[~parts.in_scope].groupby("pr_id").path.agg(set).to_dict()
    cat = parts[~parts.in_scope].groupby(["pr_id", "path"]).category.agg(lambda x: ";".join(sorted(set(x)))).to_dict()
    reason = parts.groupby(["pr_id", "path"]).reason.agg(lambda x: " | ".join(dict.fromkeys(x))).to_dict()
    itext = dict(zip(s.pr_id, s.issues_list.map(issue_text)))
    ftext = {(f.pr_id, f.filename): diff_text(f.filename, f.patch) for f in files.itertuples(index=False)}
    sim = tfidf_similarity([itext[p] for p in sheet.pr_id], [ftext[(p, q)] for p, q in zip(sheet.pr_id, sheet.path)])
    prow = s.set_index("pr_id")
    key = sheet[["id", "pr_id", "path"]].copy()
    key["agent"] = key.pr_id.map(prow.agent)
    key["fence_anchored"] = key.pr_id.map(prow.anchored)
    key["fence_out_of_scope"] = [p in out_paths.get(i, set()) for i, p in zip(key.pr_id, key.path)]
    key["fence_category"] = [cat.get((i, p), "") for i, p in zip(key.pr_id, key.path)]
    key["fence_reason"] = [reason.get((i, p), "") for i, p in zip(key.pr_id, key.path)]
    key["file_tfidf_dist"] = 1 - sim
    for col in ["reach", "n_flagged", "n_flagged_high", "size_lines", "n_files", "n_top_dirs", "tfidf_dist"]:
        key[f"pr_{col}"] = key.pr_id.map(prow[col])

    app = HERE.parent / "app"
    with (app / "tasks.jsonl").open("w") as fh:
        for t in tasks:
            fh.write(json.dumps(t) + "\n")
    sheet.to_csv(HERE / "gold_sheet.csv", index=False)
    key.to_csv(HERE / "key_do_not_open.csv", index=False)
    summary = {
        "corpus_prs": len(df),
        "eligible_prs": len(ok),
        "eligibility": f"1-{MAX_FILES} files and <= {MAX_LINES} changed lines",
        "eligible_by_agent": ok.agent.value_counts().to_dict(),
        "sampled_by_agent": s.agent.value_counts().to_dict(),
        "sampled_prs": len(s),
        "sampled_files": len(sheet),
        "fence_scope_unresolvable_prs": int((~s.anchored).sum()),
        "fence_reaching_prs": int((s.anchored & (s.n_flagged > 0)).sum()),
        "fence_out_of_scope_files": int(key.fence_out_of_scope.sum()),
        "seed": SEED,
    }
    (HERE / "sample_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
