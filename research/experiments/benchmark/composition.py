"""Why do some agents get flagged more often? PR size composition, missing patches and the files that get flagged.

Usage: python composition.py --corpus data/fence_bench
Reads results/pr_scores.parquet plus the corpus files and writes results/composition.{json,md}.
All rates are Fence's own flags on anchored PRs, not human-verified scope creep.
"""

from __future__ import annotations

import argparse
import json
import posixpath
from pathlib import Path

import numpy as np
import pandas as pd
from common import wilson

HERE = Path(__file__).parent
BINS = [0, 1, 2, 3, 5, 8, 16, 32, 64, np.inf]
BIN_LABELS = ["1", "2", "3", "4-5", "6-8", "9-16", "17-32", "33-64", "65+"]
AGENTS = ["Claude_Code", "Copilot", "OpenAI_Codex", "Devin", "Cursor", "Google_Jules"]


def standardized(flag: np.ndarray, b: np.ndarray, weights: np.ndarray) -> float:
    """Flag rate re-weighted to a reference file-count mix (bins with no PRs are dropped and weights renormalized)."""
    k = np.bincount(b, weights=flag, minlength=len(weights))
    n = np.bincount(b, minlength=len(weights))
    ok = n > 0
    return float(np.sum(weights[ok] * k[ok] / n[ok]) / weights[ok].sum())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    corpus, out = Path(a.corpus), Path(a.out)

    d = pd.read_parquet(HERE / "results" / "pr_scores.parquet")
    d = d.merge(pd.read_parquet(corpus / "prs.parquet", columns=["pr_id", "repo_id"]), on="pr_id")
    anc = d[d.anchored].copy()
    anc["flag"] = (anc.n_flagged > 0).astype(float)
    anc["bin"] = pd.cut(anc.n_files, BINS, labels=False).astype(int)
    ref = np.bincount(anc.bin, minlength=len(BIN_LABELS)) / len(anc)

    fr = pd.read_parquet(corpus / "file_results.parquet", columns=["pr_id", "path", "kind", "in_scope"])
    fr = fr[fr.pr_id.isin(set(anc.pr_id))]
    flagged = fr[~fr.in_scope]
    noncode_only = flagged.groupby("pr_id").kind.agg(lambda k: bool((k != "code").all()))

    files = pd.read_parquet(corpus / "files.parquet", columns=["pr_id", "patch"])
    files["missing"] = files.patch.isna() | (files.patch.fillna("").str.strip() == "")
    files = files.drop(columns="patch").merge(d[["pr_id", "agent"]], on="pr_id")

    agents = {}
    for ag in AGENTS + ["ALL"]:
        g = anc if ag == "ALL" else anc[anc.agent == ag]
        fl = g[g.flag > 0]
        nc = noncode_only.reindex(fl.pr_id).fillna(False)
        f = files if ag == "ALL" else files[files.agent == ag]
        lo, hi = wilson(int(g.flag.sum()), len(g))
        agents[ag] = {
            "anchored_prs": len(g),
            "median_files": float(g.n_files.median()),
            "median_lines": float(g.size_lines.median()),
            "share_over_16_files": round(100 * float((g.n_files > 16).mean()), 1),
            "flag_rate": round(100 * float(g.flag.mean()), 2),
            "flag_rate_ci95": [round(100 * lo, 2), round(100 * hi, 2)],
            "flag_rate_std_files": round(100 * standardized(g.flag.values, g.bin.values, ref), 1),
            "flagged_noncode_only": round(100 * float(nc.mean()), 1) if len(fl) else None,
            "file_rows_missing_patch": round(100 * float(f.missing.mean()), 2),
        }

    by_bin = []
    for i, lab in enumerate(BIN_LABELS):
        row = {"files": lab, "share_all": round(100 * ref[i], 1)}
        for ag in AGENTS:
            g = anc[(anc.agent == ag) & (anc.bin == i)]
            row[ag] = round(100 * float(g.flag.mean()), 1) if len(g) >= 30 else None
        by_bin.append(row)

    flagged = flagged.merge(anc[["pr_id", "agent"]], on="pr_id")
    flagged["base"] = flagged.path.map(lambda p: posixpath.basename(p).lower())
    per_pr = flagged.drop_duplicates(["pr_id", "base"])
    n_cop, n_oth = int((anc.agent == "Copilot").sum()), int((anc.agent != "Copilot").sum())
    cop = per_pr[per_pr.agent == "Copilot"].base.value_counts()
    oth = per_pr[per_pr.agent != "Copilot"].base.value_counts()
    top = [
        {
            "file": b,
            "copilot_prs_pct": round(100 * cop[b] / n_cop, 1),
            "other_prs_pct": round(100 * oth.get(b, 0) / n_oth, 1),
        }
        for b in cop.index[:12]
    ]

    # Flag rate of merged vs unmerged PRs, raw and standardized to the same file-count mix,
    # with a repository-clustered bootstrap CI for the standardized difference.
    m = anc.merged.values.astype(bool)
    flag, b = anc.flag.values, anc.bin.values
    raw = float(flag[m].mean() - flag[~m].mean())
    std = standardized(flag[m], b[m], ref) - standardized(flag[~m], b[~m], ref)
    rng = np.random.default_rng(0)
    _, inv = np.unique(anc.repo_id.values, return_inverse=True)
    members = np.split(np.argsort(inv, kind="stable"), np.cumsum(np.bincount(inv))[:-1])
    boots = []
    for _ in range(500):
        ix = np.concatenate([members[j] for j in rng.integers(0, len(members), len(members))])
        mm, ff, bb = m[ix], flag[ix], b[ix]
        boots.append(standardized(ff[mm], bb[mm], ref) - standardized(ff[~mm], bb[~mm], ref))
    merge = {
        "merged_flag_rate": round(100 * float(flag[m].mean()), 2),
        "unmerged_flag_rate": round(100 * float(flag[~m].mean()), 2),
        "raw_diff_pts": round(100 * raw, 2),
        "std_diff_pts": round(100 * std, 2),
        "std_diff_ci95": [round(100 * float(x), 2) for x in np.quantile(boots, [0.025, 0.975])],
    }

    res = {
        "bins": BIN_LABELS,
        "agents": agents,
        "flag_rate_by_files": by_bin,
        "copilot_top_flagged": top,
        "merge": merge,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "composition.json").write_text(json.dumps(res, indent=1) + "\n")

    md = "# Why flag rates differ by agent (Fence's own flags on anchored PRs, not human-verified)\n\n"
    md += "Standardized = flag rate re-weighted to the file-count mix of all anchored PRs.\n\n"
    md += "| agent | anchored PRs | median files | median lines | >16 files | flag rate | standardized | flags only on non-code files | file rows missing patch |\n"
    md += "|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    for ag, r in agents.items():
        md += (
            f"| {ag} | {r['anchored_prs']:,} | {r['median_files']:g} | {r['median_lines']:g} | {r['share_over_16_files']}% "
            f"| {r['flag_rate']}% | {r['flag_rate_std_files']}% | {r['flagged_noncode_only']}% | {r['file_rows_missing_patch']}% |\n"
        )
    md += "\nFlag rate by file count (cells with fewer than 30 PRs left blank):\n\n"
    md += "| files | share of PRs | " + " | ".join(AGENTS) + " |\n|---|---:|" + "---:|" * len(AGENTS) + "\n"
    for r in by_bin:
        md += (
            f"| {r['files']} | {r['share_all']}% | "
            + " | ".join("" if r[ag] is None else f"{r[ag]}%" for ag in AGENTS)
            + " |\n"
        )
    md += "\nFiles most often flagged in Copilot PRs (share of anchored PRs with that file flagged):\n\n"
    md += "| file | Copilot | other agents |\n|---|---:|---:|\n"
    for r in top:
        md += f"| `{r['file']}` | {r['copilot_prs_pct']}% | {r['other_prs_pct']}% |\n"
    md += (
        f"\nMerged vs not merged: flag rate {merge['merged_flag_rate']}% vs {merge['unmerged_flag_rate']}% "
        f"(raw {merge['raw_diff_pts']:+} pts; standardized to the same file-count mix {merge['std_diff_pts']:+} pts, "
        f"repo-clustered 95% CI {merge['std_diff_ci95']}).\n"
    )
    (out / "composition.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
