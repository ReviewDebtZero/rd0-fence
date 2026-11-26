"""Build number macros, tables and figures for both papers from the benchmark result files (no hand-typed numbers)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RES = ROOT / "research" / "experiments" / "benchmark" / "results"
OUT = HERE.parent / "generated"
OUT.mkdir(exist_ok=True)

P = json.loads((RES / "prevalence.json").read_text())
A = json.loads((RES / "paichecker.json").read_text())
C = json.loads((RES / "composition.json").read_text())
K = json.loads((RES / "combo.json").read_text())
L = json.loads((RES / "latency.json").read_text())
G = json.loads((ROOT / "research" / "experiments" / "label_audit" / "human" / "sample_summary.json").read_text())

AGENTS = ["Claude_Code", "Copilot", "OpenAI_Codex", "Cursor", "Devin", "Google_Jules"]
NAME = {"Claude_Code": "Claude Code", "Copilot": "Copilot", "OpenAI_Codex": "Codex", "Cursor": "Cursor",
        "Devin": "Devin", "Google_Jules": "Jules"}  # fmt: skip
MAC = {"Claude_Code": "Claude", "Copilot": "Copilot", "OpenAI_Codex": "Codex", "Cursor": "Cursor", "Devin": "Devin",
       "Google_Jules": "Jules"}  # fmt: skip
SCORE = {"size_lines": "PR size (changed lines)", "n_files": "File count", "fence_reach": "Fence reach",
         "tfidf_dist": "TF-IDF issue/diff distance", "n_top_dirs": "Top-level directories"}  # fmt: skip

macros: dict[str, str] = {}


def n(x) -> str:
    return f"{x:,}".replace(",", "{,}")


def ci(lo_hi, fmt="{:.1f}") -> str:
    return "[" + ", ".join(fmt.format(v) for v in lo_hi) + "]"


al = P["ALL"]
macros.update(
    nCorpus=n(P["corpus_prs"]),
    nAnchored=n(al["reaches"]["n"]),
    nUnres=n(al["scope_unresolvable"]["k"]),
    pctUnres=f"{al['scope_unresolvable']['pct']:.1f}",
    pctReach=f"{al['reaches']['pct']:.1f}",
    ciReach=ci(al["reaches"]["ci95"]),
    ciReachRepo=ci(al["reaches_ci95_repo_clustered"]),
    pctReachHigh=f"{al['reaches_high']['pct']:.1f}",
    ciReachHigh=ci(al["reaches_high"]["ci95"]),
    meanReach=f"{al['mean_reach_pct']:.1f}",
    ciMeanReach=ci(al["mean_reach_ci95"]),
    medianReach=f"{al['median_reach_pct']:.1f}",
    nRepos=n(C["corpus"]["repos"]),
    nTyped=n(C["corpus"]["task_typed_prs"]),
)
for cat, key in [("unrelated code", "Unrel"), ("docs", "Docs"), ("tests", "Tests"), ("formatting", "Fmt"),
                 ("dependencies", "Deps"), ("ci", "CI")]:  # fmt: skip
    macros[f"cat{key}"] = f"{al['categories'][cat]['pct']:.1f}"
for ag in AGENTS:
    r, c = P["by_agent"][ag], C["agents"][ag]
    m = MAC[ag]
    macros[f"reach{m}"] = f"{r['reaches']['pct']:.1f}"
    macros[f"std{m}"] = f"{c['flag_rate_std_files']:.1f}"
    macros[f"files{m}"] = f"{c['median_files']:g}"
    macros[f"big{m}"] = f"{c['share_over_16_files']:.1f}"
cop = C["agents"]["Copilot"]
macros.update(
    missCopilot=f"{cop['file_rows_missing_patch']:.1f}",
    missAll=f"{C['agents']['ALL']['file_rows_missing_patch']:.1f}",
    noncodeCopilot=f"{cop['flagged_noncode_only']:.1f}",
    noncodeAll=f"{C['agents']['ALL']['flagged_noncode_only']:.1f}",
)
top = {t["file"]: t for t in C["copilot_top_flagged"]}
macros.update(
    readmeCopilot=f"{top['readme.md']['copilot_prs_pct']:.1f}",
    readmeOther=f"{top['readme.md']['other_prs_pct']:.1f}",
    instrCopilot=f"{top['copilot-instructions.md']['copilot_prs_pct']:.1f}",
    instrOther=f"{top['copilot-instructions.md']['other_prs_pct']:.1f}",
    pkgCopilot=f"{top['package.json']['copilot_prs_pct']:.1f}",
    pkgOther=f"{top['package.json']['other_prs_pct']:.1f}",
)
mg = C["merge"]
macros.update(
    mergedReach=f"{mg['merged_flag_rate']:.1f}",
    unmergedReach=f"{mg['unmerged_flag_rate']:.1f}",
    mergeRaw=f"{mg['raw_diff_pts']:+.1f}",
    mergeStd=f"{mg['std_diff_pts']:+.1f}",
    ciMergeStd=ci(mg["std_diff_ci95"]),
)
tt = P["by_task_type"]
for t, key in [("feat", "Feat"), ("fix", "Fix"), ("refactor", "Refactor"), ("docs", "DocsTask")]:
    macros[f"task{key}"] = f"{tt[t]['reaches']['pct']:.1f}"
    macros[f"taskN{key}"] = n(tt[t]["prs"])
macros["unresDocsTask"] = f"{tt['docs']['scope_unresolvable']['pct']:.1f}"

pa = A["ALL"]
macros.update(
    nPai=n(pa["instances"]),
    nPaiSC=n(pa["sc_positive"]),
    nPaiUnres=n(pa["scope_unresolvable"]),
    nPaiBench=n(A["SWE-bench"]["instances"]),
    nPaiGym=n(A["SWE-Gym"]["instances"]),
    nPaiML=n(A["SWE-bench Multilingual"]["instances"]),
    aucFence=f"{pa['auroc']['fence_reach']['auc']:.3f}",
    ciAucFence=ci(pa["auroc"]["fence_reach"]["ci95"], "{:.3f}"),
    aucSize=f"{pa['auroc']['size_lines']['auc']:.3f}",
    ciAucSize=ci(pa["auroc"]["size_lines"]["ci95"], "{:.3f}"),
    aucFiles=f"{pa['auroc']['n_files']['auc']:.3f}",
    aucTfidf=f"{pa['auroc']['tfidf_dist']['auc']:.3f}",
    aucDirs=f"{pa['auroc']['n_top_dirs']['auc']:.3f}",
    paiBudget=n(pa["fence_flag"]["flagged"]),
    precFence=f"{pa['fence_flag']['precision_pct']:.1f}",
    recFence=f"{pa['fence_flag']['recall_pct']:.1f}",
    precSize=f"{pa['baselines_at_fence_budget']['size_lines']['precision_pct']:.1f}",
    recSize=f"{pa['baselines_at_fence_budget']['size_lines']['recall_pct']:.1f}",
    cvSize=f"{K['cv_auroc']['size']['mean']:.3f}",
    cvSizeFence=f"{K['cv_auroc']['size+fence']['mean']:.3f}",
    cvDelta=f"{K['delta_size_fence_vs_size']['mean']:+.3f}",
    ciCvDelta=ci(K["delta_size_fence_vs_size"]["ci95"], "{:+.3f}"),
    tercSmall=f"{K['size_terciles']['small']['fence_auroc']:.3f}",
    tercMid=f"{K['size_terciles']['middle']['fence_auroc']:.3f}",
    tercLarge=f"{K['size_terciles']['large']['fence_auroc']:.3f}",
    latMedian=f"{L['median_ms']:.1f}",
    latPninety=f"{L['p90_ms']:.1f}",
    latPnn=f"{L['p99_ms']:.0f}",
    latN=n(L["prs"]),
    goldPRs=n(G["sampled_prs"]),
    goldFiles=n(G["sampled_files"]),
    goldUnres=n(G["fence_scope_unresolvable_prs"]),
    goldPerAgent="50",
    rhoSize=f"{P['baseline_spearman_vs_reach']['size_lines']:.2f}",
    rhoFiles=f"{P['baseline_spearman_vs_reach']['n_files']:.2f}",
)
(OUT / "numbers.tex").write_text(
    "% generated by scripts/make_paper_numbers.py\n"
    + "".join(f"\\newcommand{{\\{k}}}{{{v}\\xspace}}\n" for k, v in macros.items())
)

rows = []
for ag in AGENTS:
    r, c = P["by_agent"][ag], C["agents"][ag]
    rows.append(
        f"{NAME[ag]} & {n(r['prs'])} & {r['scope_unresolvable']['pct']:.1f} & {r['reaches']['pct']:.1f} "
        f"& {r['reaches_high']['pct']:.1f} & {r['mean_reach_pct']:.1f} & {c['median_files']:g} & {c['flag_rate_std_files']:.1f}\\\\"
    )
rows.append("\\midrule")
c = C["agents"]["ALL"]
rows.append(
    f"All & {n(al['prs'])} & {al['scope_unresolvable']['pct']:.1f} & {al['reaches']['pct']:.1f} & {al['reaches_high']['pct']:.1f} "
    f"& {al['mean_reach_pct']:.1f} & {c['median_files']:g} & {c['flag_rate_std_files']:.1f}\\\\"
)
(OUT / "tab_agents.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")

rows = []
for t in ["feat", "fix", "refactor", "docs", "test", "chore", "build"]:
    r = tt[t]
    lo, hi = r["reaches"]["ci95"]
    rows.append(
        f"{t} & {n(r['prs'])} & {r['scope_unresolvable']['pct']:.1f} & {r['reaches']['pct']:.1f} [{lo:.0f}, {hi:.0f}] & {r['mean_reach_pct']:.1f}\\\\"
    )
(OUT / "tab_tasks.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")

rows = []
for k in sorted(pa["auroc"], key=lambda k: -pa["auroc"][k]["auc"]):
    v = pa["auroc"][k]
    name = f"\\textbf{{{SCORE[k]}}}" if k == "fence_reach" else SCORE[k]
    per = " & ".join(f"{A[s]['auroc'][k]['auc']:.2f}" for s in ["SWE-bench", "SWE-Gym", "SWE-bench Multilingual"])
    rows.append(f"{name} & {v['auc']:.3f} {ci(v['ci95'], '{:.3f}')} & {per}\\\\")
(OUT / "tab_pai.tex").write_text("\n".join(rows) + "\n\\bottomrule\n")

plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(3.4, 2.1))
bins = C["bins"]
colors = {"Claude_Code": "#d97706", "Copilot": "#2563eb", "OpenAI_Codex": "#059669", "Cursor": "#7c3aed",
          "Devin": "#db2777"}  # fmt: skip
for ag, col in colors.items():
    xs = [i for i, r in enumerate(C["flag_rate_by_files"]) if r[ag] is not None]
    ax.plot(xs, [C["flag_rate_by_files"][i][ag] for i in xs], marker="o", ms=2.5, lw=1.1, color=col, label=NAME[ag])
ax.set_xticks(range(len(bins)), bins, rotation=35, fontsize=6.5)
ax.set_xlabel("files changed in the PR")
ax.set_ylabel("PRs with a Fence flag (%)")
ax.set_ylim(0, 102)
ax.legend(frameon=False, fontsize=6.5, ncol=2, loc="lower right")
fig.tight_layout(pad=0.3)
fig.savefig(OUT / "fig_bins.pdf")

fig, ax = plt.subplots(figsize=(3.4, 1.7))
order = sorted(pa["auroc"], key=lambda k: pa["auroc"][k]["auc"])
for i, k in enumerate(order):
    v = pa["auroc"][k]
    col = "#2563eb" if k == "fence_reach" else "#9ca3af"
    ax.barh(i, v["auc"] - 0.5, left=0.5, color=col, height=0.6)
    ax.plot(v["ci95"], [i, i], color="black", lw=0.8)
    ax.text(v["ci95"][1] + 0.005, i, f"{v['auc']:.3f}", va="center", fontsize=6.5)
ax.set_yticks(range(len(order)), [SCORE[k] for k in order])
ax.set_xlim(0.45, 0.85)
ax.axvline(0.5, color="black", lw=0.5, ls=":")
ax.set_xlabel("AUROC (PAIChecker labels)")
fig.tight_layout(pad=0.3)
fig.savefig(OUT / "fig_auroc.pdf")
print(f"{len(macros)} macros -> {OUT}")
