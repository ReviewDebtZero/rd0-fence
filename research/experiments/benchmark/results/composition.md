# Why flag rates differ by agent (Fence's own flags on anchored PRs, not human-verified)

Standardized = flag rate re-weighted to the file-count mix of all anchored PRs.

| agent | anchored PRs | median files | median lines | >16 files | flag rate | standardized | flags only on non-code files | file rows missing patch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Claude_Code | 38,530 | 4 | 167 | 16.8% | 52.57% | 55.9% | 20.4% | 1.34% |
| Copilot | 6,224 | 15 | 756.5 | 46.3% | 82.34% | 62.9% | 11.7% | 1.21% |
| OpenAI_Codex | 5,055 | 4 | 152 | 16.2% | 56.38% | 58.3% | 27.4% | 1.27% |
| Devin | 910 | 3 | 178 | 12.6% | 49.89% | 57.0% | 16.7% | 1.29% |
| Cursor | 750 | 5 | 238 | 19.3% | 67.6% | 66.5% | 18.5% | 2.61% |
| Google_Jules | 228 | 2 | 78 | 11.0% | 40.35% | 57.9% | 13.0% | 1.32% |
| ALL | 51,697 | 5 | 204 | 20.2% | 56.64% | 56.6% | 19.5% | 1.31% |

Flag rate by file count (cells with fewer than 30 PRs left blank):

| files | share of PRs | Claude_Code | Copilot | OpenAI_Codex | Devin | Cursor | Google_Jules |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 15.3% | 11.7% | 19.0% | 16.6% | 13.8% | 21.1% | 6.6% |
| 2 | 16.5% | 22.6% | 32.5% | 15.4% | 16.8% | 36.5% | 18.8% |
| 3 | 10.4% | 49.9% | 61.6% | 61.3% | 43.1% | 60.8% |  |
| 4-5 | 13.1% | 60.3% | 72.8% | 63.0% | 64.8% | 72.5% |  |
| 6-8 | 11.3% | 70.6% | 84.3% | 75.3% | 76.7% | 85.4% |  |
| 9-16 | 13.2% | 79.2% | 84.5% | 81.6% | 82.4% | 90.4% |  |
| 17-32 | 7.7% | 88.7% | 88.1% | 91.7% | 93.5% | 94.8% |  |
| 33-64 | 5.1% | 94.5% | 90.0% | 96.0% |  | 100.0% |  |
| 65+ | 7.5% | 98.0% | 90.1% | 99.7% | 98.4% | 100.0% |  |

Files most often flagged in Copilot PRs (share of anchored PRs with that file flagged):

| file | Copilot | other agents |
|---|---:|---:|
| `readme.md` | 11.4% | 6.6% |
| `package.json` | 7.9% | 3.3% |
| `.gitignore` | 6.4% | 3.6% |
| `changelog.md` | 5.8% | 4.6% |
| `copilot-instructions.md` | 5.0% | 0.1% |
| `package-lock.json` | 4.6% | 1.3% |
| `global.json` | 3.3% | 0.0% |
| `tsconfig.json` | 3.1% | 0.9% |
| `index.ts` | 2.6% | 1.8% |
| `makefile` | 2.2% | 0.8% |
| `settings.json` | 2.0% | 0.5% |
| `pnpm-lock.yaml` | 2.0% | 0.9% |

Merged vs not merged: flag rate 57.88% vs 54.08% (raw +3.8 pts; standardized to the same file-count mix -0.47 pts, repo-clustered 95% CI [-4.52, 2.85]).
