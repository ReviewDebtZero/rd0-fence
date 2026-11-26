# Dataset survey (milestone 1)

Sizes were measured on 2026-11-22: total file size from the Hugging Face Hub API, row counts from the dataset
card or from the parquet footers we downloaded. "Usable" means the PR links at least one issue with 30 or more
characters of body text (see `research/experiments/feasibility/`).

## Candidate datasets

| Dataset (Hugging Face id) | Size | Rows | License | Issue text | PR diff | Agent PRs | Use for Fence |
|---|---:|---:|---|---|---|---|---|
| `hao-li/AIDev` (v5, AIDev-pop tables) | 22,367 MB repo; pop PR table 362 MB | 361,296 pop PRs; 100,050 PR-issue links; 12,116,310 commit-file rows | CC BY 4.0 | yes | yes, per commit file | yes, 6 agents | **main corpus** |
| `hao-li/AIDev-full` (v3) | 3,371 MB | 931,785 PRs; 33,596 with task type; 33,239 PR-issue links | CC BY 4.0 | yes | yes, except Copilot | yes, 5 agents | task-type labels |
| `hao-li/AIDev-2.7M` (v4) | 3,113 MB | not counted | CC BY 4.0 | yes | yes | yes | superseded by v5 |
| `manyiResearch/PAIChecker` labels (GitHub) | 3 CSV files | 503 + 2,287 + 300 labelled instances | MIT | yes | gold patch | no (human PRs) | **external labels**: scope creep (SC) = 22, 400, 33 |
| `SWE-bench/SWE-bench_Verified` | 6.3 MB | 500 | none in card | yes | gold patch | no | joins PAIChecker labels |
| `SWE-bench/SWE-bench` | 36.6 MB | 2,294 test + 225 dev | none in card | yes | gold patch | no | more issue/patch pairs |
| `SWE-bench/SWE-bench_Lite` | 2.9 MB | 300 + 23 | none in card | yes | gold patch | no | subset of above |
| `SWE-bench/SWE-bench_Multilingual` | 1.9 MB | 300 | MIT | yes | gold patch | no | joins PAIChecker labels |
| `SWE-Gym/SWE-Gym` | 43.6 MB | 2,438 | MIT | yes | gold patch | no | joins PAIChecker labels |
| `SWE-Gym/SWE-Gym-Raw` | 728.5 MB | 64,689 | none in card | yes | gold patch | no | human baseline pool |
| `nebius/SWE-rebench` | 245.2 MB | 21,336 + 6,542 | CC BY 4.0 | yes | gold patch | no | human baseline pool |
| `nebius/SWE-rebench-V2-PRs` | 2,682 MB | 126,300 | CC BY 4.0 | yes | yes | no | human baseline pool |
| `SWE-bench-Live/SWE-bench-Live` | 240.4 MB | 1,888 full | MIT | yes | gold patch | no | recent, less contamination |
| `ScaleAI/SWE-bench_Pro` | 15.1 MB | 1,424 | none in card | yes | gold patch | no | optional |
| `ByteDance-Seed/Multi-SWE-bench` | 1,796 MB | not counted | other | yes | gold patch | no | optional, multi-language |
| `AmazonScience/SWE-PolyBench` | 100.4 MB | not counted | MIT | yes | gold patch | no | optional |
| `SWE-bench/SWE-smith` | 277.8 MB | 59,136 | MIT | synthetic | synthetic | no | not used (synthetic issues) |
| `wenhana/PullRequest-issues` | 35,412 MB | not counted | none in card | yes | yes | no | not used (no license) |
| `Qodo/PR-Review-Bench` | 0.6 MB | about 100 PRs | MIT | no | yes | mixed | not used (no issue) |
| GHPR (`soroushj/ghpr`, GitHub only) | not measured | 14,384 issue-PR pairs (paper) | see repo | yes | yes | no | optional |

## What AIDev gives us

From `research/experiments/feasibility/results/feasibility.json` (AIDev v5 pop):

| Agent | PRs | Linked to an issue | Usable issue text | Usable + diff rows | Usable + >=90% of file rows have a patch | Usable + merged |
|---|---:|---:|---:|---:|---:|---:|
| Claude Code | 172,597 | 43,454 | 42,858 | 42,716 | 40,259 | 29,662 |
| Copilot | 98,384 | 18,942 | 18,493 | 17,675 | 6,549 | 11,501 |
| OpenAI Codex | 62,731 | 5,757 | 5,661 | 5,656 | 5,258 | 3,079 |
| Cursor | 12,908 | 859 | 845 | 845 | 786 | 550 |
| Devin | 11,219 | 1,046 | 1,029 | 1,029 | 961 | 467 |
| Google Jules | 3,457 | 277 | 271 | 271 | 245 | 148 |
| **All** | **361,296** | **70,335** | **69,157 (19.1%)** | **68,192** | **54,058** | **45,407** |

Usable PRs come from 8,548 repositories. 53,176 link exactly one issue. Issue bodies (links with >=30 chars)
have a median of 1,270 characters (10th to 90th percentile: 201 to 4,831).

Caveats we measured:
- Copilot has many file rows with no `patch` (only 788 of its usable PRs have a patch on every row), so Copilot
  counts drop most under the 90% patch filter. This must be reported, not hidden.
- AIDev v5 has no task-type table. AIDev-full (v3) has one for 33,596 pop PRs, of which 4,766 are usable
  (fix 2,194; feat 1,514; docs 382; refactor 239; test 134; chore 115; build 91; ci 49; perf 36; other 18).
  AIDev-full has no commit details for Copilot PRs.
- Diffs are rebuilt from per-commit file patches, so a file touched by several commits appears several times.
  The benchmark will merge them per file, or use the PR-level diff from the GitHub API for the gold sample.

## Prior work this builds on (verified)

| Work | What it measures | Gap Fence targets |
|---|---|---|
| Revert study on agent PRs, MSR 2026 (doi 10.1145/3793302.3793587) | 33,580 agent PRs, 2.66% with a revert; revert causes: unintended side effects 22.33%, overengineering 22.13%, functional incorrectness 17.71% | motivation only |
| PR-MCI, arXiv 2601.04886 | PR **description** vs code; 23,247 agent PRs, 974 annotated, 1.7% high-MCI | issue vs diff is not measured |
| PAIChecker, arXiv 2607.28587 (ASE 2026) | PR-issue misalignment in SWE-bench-style data (13.6% in Verified), LLM multi-agent, PR-level labels incl. scope creep | human PRs in benchmarks; LLM; no part-level output |
| Işık et al., FORGE 2025; Altunhan et al., arXiv 2609.01087 | LLM classifies issue-PR pairs as Exact / Missing / Tangling (194 and 400 pairs) | small human-PR sets; LLM; PR-level |
| Overeager Coding Agents (arXiv 2605.18583), SWE-Misbehavior (arXiv 2610.18206) | out-of-scope agent actions in sandboxes / synthetic tasks | not real merged PRs |
| Refactoring Runaway (arXiv 2605.22526) | tangled refactorings in agent patches | refactoring only |
| Tangled-change work (Herzig and Zeller; SCAM 2018 slicing; CoRA, ASE 2019; UTango) | split a commit into concerns | no issue as the reference |
| Industry: Meta ARCTIC (arXiv 2607.29516); Microsoft over-edit DRA (arXiv 2611.34875) | LLM drift / unrequested-change scoring against chat intent (Meta, internal); trajectory replay + test reruns to find unneeded edits (SWE-bench Verified, DeepSWE) | need an LLM, trajectories or tests; internal or benchmark data, not issue vs diff on public agent PRs |
| Tools: Verdict, pr-guardrails, intentguard, Commitor | LLM PR-vs-ticket or tangled-commit checks | need an API key; no published evaluation |

Defensible gap: nobody has measured, on real agent PRs at scale, how much of a diff falls outside its linked
issue, with a deterministic, part-level (file and hunk) check that gives a reason per part and runs without an LLM.
