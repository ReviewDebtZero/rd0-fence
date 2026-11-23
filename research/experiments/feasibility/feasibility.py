"""How many AIDev agent PRs link an issue whose text we can compare against the PR diff?

Reads local AIDev parquet files (Hugging Face: hao-li/AIDev = v5, hao-li/AIDev-full = v3; both CC BY 4.0) and
writes results/feasibility.json. CPU only, needs duckdb. Download the files first, for example:

    hf download hao-li/AIDev --repo-type dataset --local-dir data/aidev \
        --include pull_request.parquet related_issue.parquet issue.parquet pr_commit_details.parquet
    hf download hao-li/AIDev-full --repo-type dataset --local-dir data/aidev_full \
        --include pull_request.parquet pr_task_type.parquet related_issue.parquet issue.parquet pr_commit_details.parquet

Usage: python feasibility.py --v5 data/aidev --v3 data/aidev_full
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

MIN_ISSUE_CHARS = 30


def usable_sql(d: str, extra_pr_filter: str = "") -> str:
    """PRs with >=1 linked issue whose title+body has at least MIN_ISSUE_CHARS characters of body text."""
    return f"""
    with pr as (select id, agent, repo_id, merged_at from read_parquet('{d}/pull_request.parquet') {extra_pr_filter}),
    link as (
      select r.pr_id, r.issue_id, length(coalesce(i.body, '')) as blen
      from read_parquet('{d}/related_issue.parquet') r
      join read_parquet('{d}/issue.parquet') i on i.id = r.issue_id
      where r.pr_id in (select id from pr)
    ),
    per_pr as (
      select pr_id, count(*) as n_issues, sum(case when blen >= {MIN_ISSUE_CHARS} then 1 else 0 end) as n_text
      from link group by pr_id
    )
    select pr.id, pr.agent, pr.repo_id, pr.merged_at is not null as merged,
           coalesce(per_pr.n_issues, 0) as n_issues, coalesce(per_pr.n_text, 0) as n_text
    from pr left join per_pr on per_pr.pr_id = pr.id
    """


def diff_cov_sql(d: str) -> str:
    return f"""
    select pr_id, count(*) as nrows, count(patch) as npatched, count(distinct filename) as nfiles,
           count(distinct sha) as ncommits
    from read_parquet('{d}/pr_commit_details.parquet') group by pr_id
    """


def summarize(con, d: str, extra: str = "") -> dict:
    con.execute(f"create or replace temp table u as {usable_sql(d, extra)}")
    con.execute(f"create or replace temp table c as {diff_cov_sql(d)}")
    q = """
    select agent, count(*) prs,
      sum((n_issues > 0)::int) linked,
      sum((n_text > 0)::int) usable,
      sum((n_text = 1 and n_issues = 1)::int) single_issue,
      sum((n_text > 0 and merged)::int) usable_merged,
      sum((n_text > 0 and c.nfiles > 0)::int) usable_with_diff,
      sum((n_text > 0 and c.nfiles > 0 and c.npatched = c.nrows)::int) usable_full_patch,
      sum((n_text > 0 and c.nfiles > 0 and c.npatched >= 0.9 * c.nrows)::int) usable_90pct_patch
    from u left join c on c.pr_id = u.id group by rollup(agent) order by prs desc
    """
    cols = [x[0] for x in con.execute(q).description]
    rows = [dict(zip(cols, r)) for r in con.execute(q).fetchall()]
    for r in rows:
        r["agent"] = r["agent"] or "ALL"
        r["usable_pct"] = round(100 * r["usable"] / r["prs"], 2)
    repos = con.execute("select count(distinct repo_id) from u where n_text > 0").fetchone()[0]
    qs = con.execute(
        f"""select quantile_cont(blen, [0.1, 0.25, 0.5, 0.75, 0.9]) from (
          select length(coalesce(i.body, '')) blen from read_parquet('{d}/related_issue.parquet') r
          join read_parquet('{d}/issue.parquet') i on i.id = r.issue_id where length(coalesce(i.body, '')) >= {MIN_ISSUE_CHARS})"""
    ).fetchone()[0]
    return {"by_agent": rows, "repos_with_usable_pr": repos, "issue_body_chars_q10_25_50_75_90": [round(x) for x in qs]}


def task_types(con, d: str) -> list[dict]:
    q = f"""
    select t.type, count(*) prs, sum((u.n_text > 0)::int) usable
    from read_parquet('{d}/pr_task_type.parquet') t join u on u.id = t.id group by t.type order by prs desc
    """
    return [{"type": a, "prs": b, "usable": c} for a, b, c in con.execute(q).fetchall()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v5", required=True, help="dir with hao-li/AIDev (v5) parquet files")
    ap.add_argument("--v3", help="dir with hao-li/AIDev-full (v3) parquet files")
    ap.add_argument("--out", default=str(Path(__file__).parent / "results" / "feasibility.json"))
    a = ap.parse_args()
    con = duckdb.connect()
    con.execute("set enable_progress_bar=false")
    out = {"min_issue_body_chars": MIN_ISSUE_CHARS, "aidev_v5_pop": summarize(con, a.v5)}
    if a.v3:
        pop = f"where id in (select id from read_parquet('{a.v3}/pr_task_type.parquet'))"
        out["aidev_v3_pop"] = summarize(con, a.v3, pop)
        out["aidev_v3_pop"]["task_types"] = task_types(con, a.v3)
    Path(a.out).write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    main()
