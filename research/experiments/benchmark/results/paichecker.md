# Fence vs PAIChecker scope-creep labels (human labels on gold SWE patches)

| set | instances | SC | unresolvable | AUROC fence_reach | AUROC size_lines | AUROC n_files | AUROC n_top_dirs | AUROC tfidf_dist |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | 3,087 | 455 | 21 | 0.577 [0.554, 0.601] | 0.757 [0.733, 0.779] | 0.673 [0.646, 0.698] | 0.51 [0.489, 0.532] | 0.577 [0.55, 0.603] |
| SWE-bench | 500 | 22 | 3 | 0.541 [0.468, 0.635] | 0.75 [0.645, 0.834] | 0.643 [0.538, 0.743] | 0.522 [0.497, 0.574] | 0.69 [0.604, 0.781] |
| SWE-Gym | 2,287 | 400 | 13 | 0.563 [0.538, 0.588] | 0.74 [0.713, 0.765] | 0.645 [0.612, 0.674] | 0.478 [0.454, 0.503] | 0.564 [0.532, 0.595] |
| SWE-bench Multilingual | 300 | 33 | 5 | 0.66 [0.57, 0.751] | 0.751 [0.661, 0.828] | 0.696 [0.597, 0.79] | 0.594 [0.504, 0.683] | 0.523 [0.422, 0.617] |

Binary flags on ALL (baselines flag the same number of instances as Fence's any-flag rule):

| rule | flagged | precision [95% CI] | recall [95% CI] |
|---|---:|---:|---:|
| Fence any flag | 769 | 23.0% [20.2, 26.1] | 38.9% [34.5, 43.5] |
| Fence high-severity flag | 499 | 26.9% [23.2, 30.9] | 29.5% [25.4, 33.8] |
| top-k size_lines | 769 | 31.9% [28.7, 35.2] | 53.8% [49.3, 58.4] |
| top-k n_files | 769 | 28.7% [25.7, 32.0] | 48.6% [44.0, 53.2] |
| top-k n_top_dirs | 769 | 15.1% [12.7, 17.8] | 25.5% [21.7, 29.7] |
| top-k tfidf_dist | 769 | 18.9% [16.2, 21.8] | 31.9% [27.8, 36.3] |
