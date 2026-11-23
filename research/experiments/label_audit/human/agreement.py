"""Score human labels for the Fence gold sheet.

Accepts app answer files (app/answers/<name>.jsonl) and filled copies of human/gold_sheet.csv interchangeably.
Repeated saves are allowed: the last save per id wins (per PR for .jsonl, per file row for .csv).

Usage (from research/experiments/label_audit/):
    python human/agreement.py app/answers/a.jsonl app/answers/b.jsonl
Writes human/agreement.json with, per annotator: PRs labelled, how many were marked scope unresolvable, file label
counts, and Fence / baseline precision-recall against that annotator; and pairwise Cohen's kappa between annotators.
"""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "benchmark"))
from common import bootstrap, wilson  # noqa: E402

TASKS = [json.loads(x) for x in (HERE.parent / "app" / "tasks.jsonl").read_text().splitlines()]
PR_BASELINES = ["pr_reach", "pr_size_lines", "pr_n_files", "pr_n_top_dirs", "pr_tfidf_dist"]


def load(path: str) -> pd.DataFrame:
    """One row per labelled file: id, pr_id, path, label (in|out|unsure), unresolvable."""
    p = Path(path)
    if p.suffix == ".jsonl":
        rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
        ans = pd.DataFrame(rows).drop_duplicates("id", keep="last").set_index("id")
        out = []
        for t in TASKS:
            if t["id"] not in ans.index:
                continue
            a = ans.loc[t["id"]]
            for f in t["files"]:
                lab = "out" if f["path"] in a.out_of_scope else "unsure" if f["path"] in a.cant_tell else "in"
                out.append(
                    {
                        "id": f"{t['id']}::{f['path']}",
                        "pr_id": t["id"],
                        "path": f["path"],
                        "label": lab,
                        "unresolvable": bool(a.unresolvable),
                    }
                )
        return pd.DataFrame(out, columns=["id", "pr_id", "path", "label", "unresolvable"])
    d = pd.read_csv(p, dtype=str).fillna("").drop_duplicates("id", keep="last")
    unres = d.pr_scope_unresolvable.str.strip().str.lower().isin(["1", "y", "yes", "true", "x"])
    d["unresolvable"] = unres.groupby(d.pr_id).transform("any")
    blank = d.label.str.strip() == ""
    d = d[~blank | d.unresolvable].copy()
    d.loc[d.label.str.strip() == "", "label"] = "unsure"
    norm = {
        "in": "in",
        "in scope": "in",
        "out": "out",
        "out of scope": "out",
        "unsure": "unsure",
        "can't tell": "unsure",
    }
    d["label"] = d.label.str.strip().str.lower().map(norm)
    if d.label.isna().any():
        raise SystemExit(f"{path}: labels must be one of {sorted(set(norm))}")
    return d[["id", "pr_id", "path", "label", "unresolvable"]]


def prf(y, p) -> dict:
    y, p = np.asarray(y, bool), np.asarray(p, bool)
    tp, fp, fn = int((y & p).sum()), int((~y & p).sum()), int((y & ~p).sum())

    def ci(k, n):
        return [round(x, 3) for x in wilson(k, n)] if n else None

    return {
        "n": int(len(y)),
        "positives": int(y.sum()),
        "flagged": int(p.sum()),
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "precision_ci95": ci(tp, tp + fp),
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "recall_ci95": ci(tp, tp + fn),
    }


def auc(y, x, groups=None) -> dict | None:
    y, x = np.asarray(y, bool), np.asarray(x, float)
    if y.all() or not y.any():
        return None
    lo, hi = bootstrap(roc_auc_score, y, x, n=1000, groups=groups)
    return {"auc": round(float(roc_auc_score(y, x)), 3), "ci95": [round(lo, 3), round(hi, 3)]}


def score(d: pd.DataFrame, key: pd.DataFrame) -> dict:
    prs = d.groupby("pr_id").unresolvable.first()
    out = {
        "prs_labelled": int(len(prs)),
        "scope_unresolvable_prs": int(prs.sum()),
        "file_labels": d[~d.unresolvable].label.value_counts().to_dict(),
    }
    m = d.merge(key, on="id", suffixes=("", "_key"))
    pr_key = key.drop_duplicates("pr_id").set_index("pr_id")
    fence_unres = ~pr_key.loc[prs.index.astype(key.pr_id.dtype), "fence_anchored"].astype(bool).values
    out["unresolvable_vs_fence"] = {
        "human_and_fence": int((prs.values & fence_unres).sum()),
        "human_only": int((prs.values & ~fence_unres).sum()),
        "fence_only": int((~prs.values & fence_unres).sum()),
    }
    f = m[~m.unresolvable & (m.label != "unsure")]
    y = f.label == "out"
    out["file_level"] = {
        "fence": prf(y, f.fence_out_of_scope.astype(str) == "True"),
        "fence_anchored_prs_only": prf(
            y[f.fence_anchored.astype(str) == "True"],
            f[f.fence_anchored.astype(str) == "True"].fence_out_of_scope.astype(str) == "True",
        ),
        "auroc_file_tfidf_dist": auc(y, f.file_tfidf_dist, groups=f.pr_id.values),
    }
    # A PR is a human positive if any file is out of scope; with no out-of-scope file but some "can't tell" files
    # it is undecided and left out. Fence's PR verdict uses all files, judged or not.
    pr = (
        m[~m.unresolvable]
        .groupby("pr_id")
        .agg(
            has_out=("label", lambda s: (s == "out").any()),
            has_unsure=("label", lambda s: (s == "unsure").any()),
            anchored=("fence_anchored", "first"),
            n_flagged=("pr_n_flagged", "first"),
            **{b: (b, "first") for b in PR_BASELINES},
        )
    )
    pr = pr[pr.has_out | ~pr.has_unsure]
    pr["human"] = pr.has_out
    pr["fence"] = (pr.anchored.astype(str) == "True") & (pr.n_flagged > 0)
    out["pr_level"] = {"fence": prf(pr.human, pr.fence), "auroc": {b: auc(pr.human, pr[b]) for b in PR_BASELINES}}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("answers", nargs="+")
    ap.add_argument("--out", default=str(HERE / "agreement.json"))
    a = ap.parse_args()
    key = pd.read_csv(HERE / "key_do_not_open.csv", dtype={"pr_id": str})
    names = [Path(p).stem for p in a.answers]
    if len(set(names)) != len(names):
        raise SystemExit(f"answer files need distinct names (got {names}); rename them, e.g. a.jsonl and b.jsonl")
    sheets = {n: load(p) for n, p in zip(names, a.answers)}
    res = {"annotators": {n: score(d, key) for n, d in sheets.items()}, "pairwise": {}}
    for (na, da), (nb, db) in combinations(sheets.items(), 2):
        j = da.merge(db, on="id", suffixes=("_a", "_b"))
        pa = j.groupby("pr_id_a")[["unresolvable_a", "unresolvable_b"]].first()
        both = j[~j.unresolvable_a & ~j.unresolvable_b]
        res["pairwise"][f"{na}_vs_{nb}"] = {
            "shared_prs": int(len(pa)),
            "kappa_unresolvable": round(float(cohen_kappa_score(pa.unresolvable_a, pa.unresolvable_b)), 3)
            if len(pa) > 1
            else None,
            "shared_files": int(len(both)),
            "kappa_file_label": round(float(cohen_kappa_score(both.label_a, both.label_b)), 3)
            if len(both) > 1
            else None,
            "raw_file_agreement": round(float((both.label_a == both.label_b).mean()), 3) if len(both) else None,
        }
    Path(a.out).write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
