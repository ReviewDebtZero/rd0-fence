"""Build the Fence benchmark corpus from AIDev v5 (hao-li/AIDev, CC BY 4.0).

Corpus = agent PRs that link at least one issue with >= 30 characters of body text and whose commit-file rows are
at least 90% patched (54,058 PRs in the v5 snapshot; see ../feasibility). Writes, under --out (outside git):

- prs.parquet: one row per PR (agent, repo, merged, PR title/body, linked issues as JSON, v3 task type if any)
- files.parquet: one row per (PR, file): status, summed additions/deletions, and every commit's patch for that file
  joined (AIDev stores per-commit file rows without commit dates, not a squashed PR diff)

Usage: python build_corpus.py --v5 data/aidev --v3 data/aidev_full --out data/fence_bench
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

MIN_ISSUE_CHARS = 30
MIN_PATCHED = 0.9


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v5", required=True)
    ap.add_argument("--v3", help="AIDev-full dir, for conventional-commit task types")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("set enable_progress_bar=false; set preserve_insertion_order=false")
    d = a.v5
    con.execute(f"""
    create temp table iss as
      select r.pr_id, i.number, i.title, i.body, i.html_url
      from read_parquet('{d}/related_issue.parquet') r join read_parquet('{d}/issue.parquet') i on i.id = r.issue_id
      where length(coalesce(i.body, '')) >= {MIN_ISSUE_CHARS}
    """)
    con.execute(f"""
    create temp table cov as
      select pr_id, count(*) nrows, count(patch) npatched, count(distinct filename) nfiles
      from read_parquet('{d}/pr_commit_details.parquet')
      where pr_id in (select pr_id from iss) group by pr_id
    """)
    con.execute(f"""
    create temp table keep as select pr_id from cov where nfiles > 0 and npatched >= {MIN_PATCHED} * nrows
    """)
    task = (
        f"left join read_parquet('{a.v3}/pr_task_type.parquet') t on t.id = p.id"
        if a.v3
        else "left join (select null::bigint id, null::varchar type) t on false"
    )
    con.execute(f"""
    copy (
      select p.id pr_id, p.agent, p.number, p.html_url, p.repo_url, p.repo_id, p.merged_at is not null merged,
             p.title pr_title, p.body pr_body, t.type task_type,
             (select to_json(list({{'number': i.number, 'title': i.title, 'body': i.body, 'url': i.html_url}}))
              from iss i where i.pr_id = p.id) issues
      from read_parquet('{d}/pull_request.parquet') p {task}
      where p.id in (select pr_id from keep)
    ) to '{out}/prs.parquet' (format parquet)
    """)
    con.execute(f"""
    copy (
      select c.pr_id, c.filename,
             last(c.status) status,
             sum(c.additions)::int additions, sum(c.deletions)::int deletions,
             count(c.patch) n_patches, count(*) n_rows,
             string_agg(c.patch, chr(10)) patch
      from read_parquet('{d}/pr_commit_details.parquet') c
      where c.pr_id in (select pr_id from keep) and c.filename is not null
      group by c.pr_id, c.filename
    ) to '{out}/files.parquet' (format parquet)
    """)
    n = con.execute(f"select count(*), count(distinct agent) from '{out}/prs.parquet'").fetchone()
    f = con.execute(f"select count(*) from '{out}/files.parquet'").fetchone()[0]
    print(f"prs={n[0]} agents={n[1]} file_rows={f}")


if __name__ == "__main__":
    main()
