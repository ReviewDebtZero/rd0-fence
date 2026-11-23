"""Does Fence add anything to PR size on PAIChecker's scope-creep labels?

Cross-validated logistic regression (5 folds x 10 seeds) on the same 3,087 instances as paichecker.py, a paired
bootstrap of the AUROC gain over size alone, and Fence's AUROC inside PR-size terciles.
Usage: same --labels/--swebench/--swegym/--multilingual arguments as paichecker.py.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
import paichecker as pc
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict

HERE = Path(__file__).parent
MODELS = {
    "size": ["lsize"],
    "size+files": ["lsize", "lfiles"],
    "fence": ["fence_reach", "fence_flag"],
    "size+fence": ["lsize", "fence_reach", "fence_flag"],
    "size+files+fence": ["lsize", "lfiles", "fence_reach", "fence_flag"],
}


def cv_pred(X: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    return cross_val_predict(LogisticRegression(max_iter=1000), X, y, cv=cv, method="predict_proba")[:, 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    for k in ("labels", "swebench", "swegym", "multilingual"):
        ap.add_argument(f"--{k}", required=True)
    ap.add_argument("--out", default=str(HERE / "results"))
    a = ap.parse_args()
    warnings.filterwarnings("ignore")
    d = pc.run_fence(pc.load(a))
    y = d.sc.values.astype(int)
    d["lsize"], d["lfiles"] = np.log1p(d.size_lines), np.log1p(d.n_files)
    d["fence_flag"] = d.fence_flag.astype(int)

    models = {}
    for name, cols in MODELS.items():
        aucs = [roc_auc_score(y, cv_pred(d[cols].values, y, s)) for s in range(10)]
        models[name] = {"mean": round(float(np.mean(aucs)), 3), "min": round(min(aucs), 3), "max": round(max(aucs), 3)}

    p0 = cv_pred(d[MODELS["size"]].values, y, 0)
    p1 = cv_pred(d[MODELS["size+fence"]].values, y, 0)
    rng = np.random.default_rng(0)
    diffs = []
    for _ in range(2000):
        i = rng.integers(0, len(y), len(y))
        if y[i].min() != y[i].max():
            diffs.append(roc_auc_score(y[i], p1[i]) - roc_auc_score(y[i], p0[i]))
    delta = {
        "mean": round(float(np.mean(diffs)), 3),
        "ci95": [round(float(x), 3) for x in np.percentile(diffs, [2.5, 97.5])],
    }

    d["tercile"] = pd.qcut(d.size_lines.rank(method="first"), 3, labels=["small", "middle", "large"])
    terciles = {
        str(t): {
            "instances": len(g),
            "scope_creep": int(g.sc.sum()),
            "fence_auroc": round(float(roc_auc_score(g.sc, g.fence_reach)), 3),
            "size_auroc": round(float(roc_auc_score(g.sc, g.size_lines)), 3),
        }
        for t, g in d.groupby("tercile", observed=True)
    }
    res = {
        "instances": len(d),
        "positives": int(y.sum()),
        "cv_auroc": models,
        "delta_size_fence_vs_size": delta,
        "size_terciles": terciles,
    }
    out = Path(a.out)
    (out / "combo.json").write_text(json.dumps(res, indent=1) + "\n")
    md = f"# Fence + PR size on PAIChecker scope-creep labels ({len(d):,} instances, {int(y.sum())} positive)\n\n"
    md += "5-fold cross-validated logistic regression, 10 seeds (size and file count log-transformed).\n\n"
    md += "| features | CV AUROC mean | min | max |\n|---|---:|---:|---:|\n"
    for k, v in models.items():
        md += f"| {k} | {v['mean']} | {v['min']} | {v['max']} |\n"
    md += f"\nPaired bootstrap AUROC gain of size+fence over size alone (seed 0): {delta['mean']:+} {delta['ci95']}\n\n"
    md += "| size tercile | instances | scope creep | Fence AUROC | size AUROC |\n|---|---:|---:|---:|---:|\n"
    for k, v in terciles.items():
        md += f"| {k} | {v['instances']} | {v['scope_creep']} | {v['fence_auroc']} | {v['size_auroc']} |\n"
    (out / "combo.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
