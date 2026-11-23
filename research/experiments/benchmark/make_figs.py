"""Draw assets/fig_benchmark.png from results/prevalence.json and results/paichecker.json.

Usage: python make_figs.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAMES = {
    "Claude_Code": "Claude Code",
    "Copilot": "Copilot",
    "OpenAI_Codex": "Codex",
    "Devin": "Devin",
    "Cursor": "Cursor",
    "Google_Jules": "Jules",
}
SCORES = [
    ("size_lines", "PR size"),
    ("n_files", "File count"),
    ("fence_reach", "Fence"),
    ("tfidf_dist", "TF-IDF"),
    ("n_top_dirs", "Top-level dirs"),
]


def main() -> None:
    prev = json.loads((HERE / "results" / "prevalence.json").read_text())
    pai = json.loads((HERE / "results" / "paichecker.json").read_text())["ALL"]
    len_inst = pai["instances"]
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})

    agents = [k for k in prev["by_agent"] if k in NAMES]
    rows = [("All", prev["ALL"])] + [(NAMES[k], prev["by_agent"][k]) for k in agents]
    rows = rows[:1] + sorted(rows[1:], key=lambda r: r[1]["reaches"]["pct"])
    y = range(len(rows))
    pct = [r[1]["reaches"]["pct"] for r in rows]
    lo = [p - r[1]["reaches"]["ci95"][0] for p, r in zip(pct, rows)]
    hi = [r[1]["reaches"]["ci95"][1] - p for p, r in zip(pct, rows)]
    colors = ["#334155"] + ["#f59e0b"] * (len(rows) - 1)
    a.barh(list(y), pct, xerr=[lo, hi], color=colors, capsize=3)
    for i, p in enumerate(pct):
        a.text(p + hi[i] + 1.5, i, f"{p:.1f}%", va="center", fontsize=10)
    a.set_yticks(list(y), [f"{r[0]} (n={r[1]['prs']:,})" for r in rows])
    a.set_xlim(0, 100)
    a.set_xlabel("% of anchored PRs with at least one flagged part")
    a.set_title(
        f"Fence's flags on {prev['corpus_prs']:,} AIDev agent PRs\n(tool output, not human-verified)", fontsize=11
    )

    au = [(name, pai["auroc"][k]) for k, name in SCORES]
    au.sort(key=lambda r: r[1]["auc"])
    vals = [r[1]["auc"] for r in au]
    elo = [v - r[1]["ci95"][0] for v, r in zip(vals, au)]
    ehi = [r[1]["ci95"][1] - v for v, r in zip(vals, au)]
    b.barh(
        range(len(au)),
        vals,
        xerr=[elo, ehi],
        capsize=3,
        color=["#f59e0b" if n == "Fence" else "#64748b" for n, _ in au],
    )
    for i, v in enumerate(vals):
        b.text(v + ehi[i] + 0.008, i, f"{v:.3f}", va="center", fontsize=10)
    b.axvline(0.5, color="#94a3b8", lw=1, ls="--")
    b.set_yticks(range(len(au)), [n for n, _ in au])
    b.set_xlim(0.4, 0.85)
    b.set_xlabel("AUROC vs PAIChecker scope-creep labels")
    b.set_title(f"Ranking {len_inst:,} human-labelled SWE patches\n(PR size ranks best; Fence does not)", fontsize=11)

    fig.tight_layout()
    out = ROOT / "assets" / "fig_benchmark.png"
    fig.savefig(out, dpi=160)
    print(out)


if __name__ == "__main__":
    main()
