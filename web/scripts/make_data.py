"""Write web/src/data/fence.json from research/experiments/benchmark/results/.

Every number on the website comes from this file, so the site cannot drift from the result files.
Run it after any re-run:  python3 web/scripts/make_data.py
"""

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
R = ROOT / "research" / "experiments" / "benchmark" / "results"
SHEET = ROOT / "research" / "experiments" / "label_audit" / "human" / "sample_summary.json"
NAMES = {
    "Claude_Code": "Claude Code",
    "Copilot": "Copilot",
    "OpenAI_Codex": "Codex",
    "Devin": "Devin",
    "Cursor": "Cursor",
    "Google_Jules": "Jules",
}
SCORES = {
    "size_lines": "PR size",
    "n_files": "File count",
    "fence_reach": "Fence",
    "tfidf_dist": "TF-IDF text similarity",
    "n_top_dirs": "Top-level directories",
}

prev = json.loads((R / "prevalence.json").read_text())
pai = json.loads((R / "paichecker.json").read_text())["ALL"]
sheet = json.loads(SHEET.read_text())
a = prev["ALL"]
out = {
    "corpus_prs": prev["corpus_prs"],
    "unresolvable": a["scope_unresolvable"],
    "reaches": a["reaches"],
    "reaches_high": a["reaches_high"],
    "mean_reach": {"pct": a["mean_reach_pct"], "ci95": a["mean_reach_ci95"]},
    "categories": {k: v["pct"] for k, v in a["categories"].items()},
    "agents": sorted(
        (
            {"name": NAMES[k], "prs": v["prs"], **{f: v["reaches"][f] for f in ("pct", "ci95")}}
            for k, v in prev["by_agent"].items()
            if k in NAMES
        ),
        key=lambda r: -r["pct"],
    ),
    "paichecker": {
        "instances": pai["instances"],
        "positives": pai["sc_positive"],
        "auroc": sorted(
            ({"name": SCORES[k], "ours": k == "fence_reach", **v} for k, v in pai["auroc"].items()),
            key=lambda r: -r["auc"],
        ),
    },
    "gold": {"prs": sheet["sampled_prs"], "files": sheet["sampled_files"], "per_agent": 50},
}
dest = ROOT / "web" / "src" / "data" / "fence.json"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, indent=2) + "\n")
print(dest.relative_to(ROOT))
