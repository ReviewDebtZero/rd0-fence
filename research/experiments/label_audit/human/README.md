# Spreadsheet labels and scoring

`gold_sheet.csv` has one row per (PR, file). Fill `label` with `in scope`, `out of scope` or `can't tell`, and put
`yes` in `pr_scope_unresolvable` on any row of a PR whose issue is too vague to judge (file labels of that PR are
then ignored). If a row is duplicated, the last copy wins.

```bash
python human/agreement.py my_sheet.csv other_sheet.csv   # or app/answers/*.jsonl
```

`key_do_not_open.csv` holds Fence's verdict, category and reason for each file plus PR-level baseline scores.
It is only read by `agreement.py`.
