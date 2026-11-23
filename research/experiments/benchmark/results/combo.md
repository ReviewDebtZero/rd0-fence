# Fence + PR size on PAIChecker scope-creep labels (3,087 instances, 455 positive)

5-fold cross-validated logistic regression, 10 seeds (size and file count log-transformed).

| features | CV AUROC mean | min | max |
|---|---:|---:|---:|
| size | 0.756 | 0.756 | 0.757 |
| size+files | 0.757 | 0.756 | 0.758 |
| fence | 0.577 | 0.57 | 0.582 |
| size+fence | 0.757 | 0.756 | 0.758 |
| size+files+fence | 0.758 | 0.756 | 0.758 |

Paired bootstrap AUROC gain of size+fence over size alone (seed 0): +0.002 [-0.001, 0.005]

| size tercile | instances | scope creep | Fence AUROC | size AUROC |
|---|---:|---:|---:|---:|
| small | 1029 | 41 | 0.529 | 0.607 |
| middle | 1029 | 119 | 0.55 | 0.581 |
| large | 1029 | 295 | 0.517 | 0.653 |
