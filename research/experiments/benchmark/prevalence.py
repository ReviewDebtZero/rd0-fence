"""Fence prevalence on the AIDev corpus, by agent, task type and merge status, with 95% CIs.

Usage: python prevalence.py --corpus data/fence_bench
Reads prs.parquet, pr_results.parquet, baselines.parquet; writes results/prevalence.{json,md} and pr_scores.parquet.

Definitions (see ../../docs/experiment_design.md):
- scope unresolvable: Fence finds no concrete anchor (path, code name or matching file) in the issue, so it marks
  every part "scope unknown" and flags nothing.
- reaches: an anchored PR with at least one out-of-scope part; reaches_high: at least one high-severity part
  (unrelated code, CI, dependency changes); reach: out-of-scope changed lines / all changed lines.
Proportion CIs are Wilson intervals; the ALL row also has a repository-clustered bootstrap CI.
These are Fence's outputs, not human-verified rates: precision is measured separately on the gold sheet.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from common import bootstrap, wilson
from scipy.stats import spearmanr

HERE = Path(__file__).parent
BASELINES = ["size_lines", "n_files", "n_top_dirs", "tfidf_dist"]
CATS = ["unrelated code", "ci", "dependencies", "docs", "tests", "formatting"]


def rate(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {
        "k": int(k),
        "n": int(n),
        "pct": round(100 * k / n, 2) if n else None,
        "ci95": [round(100 * lo, 2), round(100 * hi, 2)],
    }


def summarize(df: pd.DataFrame, clustered: bool = False) -> dict:
    anc = df[df.anchored]
    out = {
        "prs": len(df),
        "scope_unresolvable": rate((~df.anchored).sum(), len(df)),
        "reaches": rate(anc.reaches.sum(), len(anc)),
        "reaches_high": rate(anc.reaches_high.sum(), len(anc)),
        "mean_reach_pct": round(100 * anc.reach.mean(), 2) if len(anc) else None,
        "mean_reach_ci95": [round(100 * x, 2) for x in bootstrap(np.mean, anc.reach.values, n=1000)]
        if len(anc) > 1
        else None,
        "median_reach_pct": round(100 * anc.reach.median(), 2) if len(anc) else None,
        "categories": {c: rate(anc[c].sum(), len(anc)) for c in CATS},
    }
    if clustered and len(anc):
        out["reaches_ci95_repo_clustered"] = [
            round(100 * x, 2)
            for x in bootstrap(np.mean, anc.reaches.values.astype(float), groups=anc.repo_id.values, n=1000)
        ]
    return out


def table(rows: dict, key: str) -> str:
    h = f"| {key} | PRs | scope unresolvable | reaches (any) | reaches (high) | mean reach |\n|---|---:|---:|---:|---:|---:|\n"
    for name, s in rows.items():
        u, r, rh = s["scope_unresolvable"], s["reaches"], s["reaches_high"]
        h += (
            f"| {name} | {s['prs']:,} | {u['k']:,} ({u['pct']}%) | {r['pct']}% [{r['ci95'][0]}, {r['ci95'][1]}] "
            f"| {rh['pct']}% [{rh['ci95'][0]}, {rh['ci95'][1]}] | {s['mean_reach_pct']}% "
            f"[{s['mean_reach_ci95'][0] if s['mean_reach_ci95'] else ''}, {s['mean_reach_ci95'][1] if s['mean_reach_ci95'] else ''}] |\n"
        )
    return h


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    c = Path(a.corpus)
    prs = pd.read_parquet(c / "prs.parquet", columns=["pr_id", "agent", "html_url", "repo_id", "merged", "task_type"])
    res = pd.read_parquet(c / "pr_results.parquet")
    base = pd.read_parquet(c / "baselines.parquet", columns=["pr_id", "tfidf_dist"])
    df = prs.merge(res, on="pr_id").merge(base, on="pr_id")
    df["reaches"] = df.anchored & (df.n_flagged > 0)
    df["reaches_high"] = df.anchored & (df.n_flagged_high > 0)
    cats = df.flag_categories.map(json.loads)
    for cat in CATS:
        df[cat] = cats.map(lambda d, cat=cat: cat in d)
    out = {"corpus_prs": len(df), "ALL": summarize(df, clustered=True)}
    out["by_agent"] = {k: summarize(g) for k, g in sorted(df.groupby("agent"), key=lambda kv: -len(kv[1]))}
    out["by_merged"] = {("merged" if k else "not merged"): summarize(g) for k, g in df.groupby("merged")}
    tt = df[df.task_type.notna()]
    out["by_task_type"] = {
        k: summarize(g) for k, g in sorted(tt.groupby("task_type"), key=lambda kv: -len(kv[1])) if len(g) >= 10
    }
    anc = df[df.anchored]
    out["baseline_spearman_vs_reach"] = {}
    for b in BASELINES:
        rho = spearmanr(anc[b], anc.reach).statistic
        out["baseline_spearman_vs_reach"][b] = round(float(rho), 3)
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    score_cols = ["pr_id", "agent", "html_url", "merged", "task_type", "anchored", "total_lines", "out_lines", "reach"]
    score_cols += ["n_flagged", "n_flagged_high", "flag_categories", *BASELINES]
    df[score_cols].to_parquet(o / "pr_scores.parquet", index=False)
    (o / "prevalence.json").write_text(json.dumps(out, indent=1) + "\n")
    md = "# Fence prevalence on AIDev v5 (machine output, not human-verified)\n\n"
    md += "Brackets are 95% CIs (Wilson for rates, bootstrap for mean reach). Rates use anchored PRs only.\n\n"
    md += table({"ALL": out["ALL"], **out["by_agent"]}, "agent") + "\n"
    md += table(out["by_merged"], "merge status") + "\n"
    md += (
        f"Task type (AIDev-full v3 labels; {len(tt):,} corpus PRs have one):\n\n"
        + table(out["by_task_type"], "task type")
        + "\n"
    )
    md += "Out-of-scope categories (share of anchored PRs with at least one such part):\n\n| category | PRs | % [95% CI] |\n|---|---:|---:|\n"
    for cat, r in out["ALL"]["categories"].items():
        md += f"| {cat} | {r['k']:,} | {r['pct']}% [{r['ci95'][0]}, {r['ci95'][1]}] |\n"
    md += "\nSpearman correlation of each baseline score with Fence's reach (anchored PRs):\n\n| baseline | rho |\n|---|---:|\n"
    md += "".join(f"| {b} | {r} |\n" for b, r in out["baseline_spearman_vs_reach"].items())
    (o / "prevalence.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
