"""Compare Fence and the four baselines with PAIChecker's human misalignment labels (scope creep = "SC").

PAIChecker (arXiv 2607.28587) hand-labelled issue/PR misalignment for SWE-bench (503 analysis instances),
SWE-Gym (2,287) and SWE-bench Multilingual (300). Each instance pairs an issue with the human-written gold patch
(test files excluded), so this checks Fence on human PRs, not agent PRs. Positive = any label containing "SC".
Instances whose patch text is missing (3 SWE-bench rows outside the HF test split) are dropped.

Usage:
  python paichecker.py --labels PAIChecker/labelled_data --swebench data/swebench.parquet \
      --swegym data/swegym.parquet --multilingual data/swebml.parquet
(the parquet files are the Hugging Face test/train splits of SWE-bench/SWE-bench, SWE-Gym/SWE-Gym and
SWE-bench/SWE-bench_Multilingual). Writes results/paichecker.json and results/paichecker.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from common import bootstrap, diff_text, tfidf_similarity, wilson
from rd0_fence import Issue, check
from rd0_fence.diff import parse_diff
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).parent
SCORES = ["fence_reach", "size_lines", "n_files", "n_top_dirs", "tfidf_dist"]


def load(a) -> pd.DataFrame:
    lab = Path(a.labels)
    sb = pd.read_csv(lab / "swe-bench-analysis.csv")[["instance_id", "label", "patch", "problem_statement"]]
    hf = pd.read_parquet(a.swebench, columns=["instance_id", "patch", "problem_statement"]).set_index("instance_id")
    # Prefer the upstream patch text: a few patches in the labelled CSV carry inline annotations.
    sb["patch"] = [hf.patch.get(i, p) for i, p in zip(sb.instance_id, sb.patch)]
    sb["problem_statement"] = [hf.problem_statement.get(i, s) for i, s in zip(sb.instance_id, sb.problem_statement)]
    sb = sb.rename(columns={"label": "human_label"}).assign(dataset="SWE-bench")
    parts = [sb]
    for name, csv, pq in [
        ("SWE-Gym", "swe_gym_all.csv", a.swegym),
        ("SWE-bench Multilingual", "swe_bench_multilingual.csv", a.multilingual),
    ]:
        d = pd.read_csv(lab / csv).merge(
            pd.read_parquet(pq, columns=["instance_id", "patch", "problem_statement"]), on="instance_id"
        )
        parts.append(d.assign(dataset=name))
    df = pd.concat(parts, ignore_index=True)
    df["problem_statement"] = df.problem_statement.fillna("")
    df["patch"] = df.patch.fillna("")
    df = df[df.patch.str.strip() != ""].reset_index(drop=True)
    df["sc"] = df.human_label.astype(str).str.contains(r"\bSC", regex=True)
    return df


def run_fence(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ps, patch in zip(df.problem_statement, df.patch):
        title, _, body = ps.strip().partition("\n")
        files = parse_diff(patch or "")
        rep = check(Issue.from_text(title, body), files)
        rows.append(
            {
                "anchored": rep.anchored,
                "fence_flag": rep.anchored and bool(rep.flagged),
                "fence_flag_high": rep.anchored and any(p.severity == "high" for p in rep.flagged),
                "fence_reach": rep.out_fraction,
                "size_lines": sum(f.changed for f in files),
                "n_files": len(files),
                "n_top_dirs": len({f.path.split("/", 1)[0] if "/" in f.path else "." for f in files}),
                "diff_text": "\n".join(
                    diff_text(f.path, "\n".join("+" + x for h in f.hunks for x in h.added + h.removed)) for f in files
                ),
            }
        )
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    out["tfidf_dist"] = 1 - tfidf_similarity(out.problem_statement.fillna("").tolist(), out.diff_text.tolist())
    return out


def prf(y: np.ndarray, p: np.ndarray) -> dict:
    tp, fp, fn = int((y & p).sum()), int((~y & p).sum()), int((y & ~p).sum())
    prec_ci, rec_ci = wilson(tp, tp + fp), wilson(tp, tp + fn)
    return {
        "flagged": int(p.sum()),
        "tp": tp,
        "precision_pct": round(100 * tp / (tp + fp), 1) if tp + fp else None,
        "precision_ci95": [round(100 * x, 1) for x in prec_ci],
        "recall_pct": round(100 * tp / (tp + fn), 1) if tp + fn else None,
        "recall_ci95": [round(100 * x, 1) for x in rec_ci],
    }


def evaluate(d: pd.DataFrame) -> dict:
    y = d.sc.values.astype(bool)
    out = {"instances": len(d), "sc_positive": int(y.sum()), "scope_unresolvable": int((~d.anchored).sum())}
    out["auroc"] = {}
    for s in SCORES:
        x = d[s].values.astype(float)
        auc = roc_auc_score(y, x) if 0 < y.sum() < len(y) else float("nan")
        lo, hi = bootstrap(roc_auc_score, y, x, n=1000)
        out["auroc"][s] = {"auc": round(float(auc), 3), "ci95": [round(lo, 3), round(hi, 3)]}
    out["fence_flag"] = prf(y, d.fence_flag.values.astype(bool))
    out["fence_flag_high"] = prf(y, d.fence_flag_high.values.astype(bool))
    k = int(d.fence_flag.sum())
    out["baselines_at_fence_budget"] = {}
    for s in SCORES[1:]:
        top = np.zeros(len(d), bool)
        if k:
            top[np.argsort(-d[s].values, kind="stable")[:k]] = True
        out["baselines_at_fence_budget"][s] = prf(y, top)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--swebench", required=True)
    ap.add_argument("--swegym", required=True)
    ap.add_argument("--multilingual", required=True)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    df = run_fence(load(a))
    res = {"ALL": evaluate(df)}
    for name, g in df.groupby("dataset", sort=False):
        res[name] = evaluate(g)
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "paichecker.json").write_text(json.dumps(res, indent=1) + "\n")
    md = "# Fence vs PAIChecker scope-creep labels (human labels on gold SWE patches)\n\n"
    md += "| set | instances | SC | unresolvable | " + " | ".join(f"AUROC {s}" for s in SCORES) + " |\n"
    md += "|---|---:|---:|---:|" + "---:|" * len(SCORES) + "\n"
    for name, r in res.items():
        md += f"| {name} | {r['instances']:,} | {r['sc_positive']} | {r['scope_unresolvable']} | "
        md += (
            " | ".join(
                f"{r['auroc'][s]['auc']} [{r['auroc'][s]['ci95'][0]}, {r['auroc'][s]['ci95'][1]}]" for s in SCORES
            )
            + " |\n"
        )
    md += "\nBinary flags on ALL (baselines flag the same number of instances as Fence's any-flag rule):\n\n"
    md += "| rule | flagged | precision [95% CI] | recall [95% CI] |\n|---|---:|---:|---:|\n"
    rows = {"Fence any flag": res["ALL"]["fence_flag"], "Fence high-severity flag": res["ALL"]["fence_flag_high"]}
    rows.update({f"top-k {s}": v for s, v in res["ALL"]["baselines_at_fence_budget"].items()})
    for name, r in rows.items():
        md += f"| {name} | {r['flagged']} | {r['precision_pct']}% {r['precision_ci95']} | {r['recall_pct']}% {r['recall_ci95']} |\n"
    (o / "paichecker.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
