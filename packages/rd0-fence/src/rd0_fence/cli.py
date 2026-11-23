"""`fence` command line: check a diff against the issue it should resolve."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

from . import __version__
from .diff import files_from_patches, parse_diff
from .issue import Issue
from .render import markdown, text
from .scope import check

PR_REF = re.compile(r"^(?:https://github\.com/)?([\w.-]+/[\w.-]+)(?:#|/pull/)(\d+)$")


def _read(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _issue(a) -> Issue:
    if a.issue:
        raw = _read(a.issue)
        if a.issue.endswith(".json"):
            d = json.loads(raw)
            return Issue.from_text(d.get("title", ""), d.get("body", ""), d.get("number"))
        first, _, rest = raw.partition("\n")
        return Issue.from_text(first.lstrip("# ").strip(), rest)
    return Issue.from_text(a.title or "", a.body or "")


def _emit(rep, a) -> int:
    if a.format == "json":
        print(json.dumps(rep.to_dict(), indent=2))
    elif a.format == "markdown":
        print(markdown(rep))
    else:
        print(text(rep))
    if a.fail_over is not None and rep.out_fraction > a.fail_over:
        return 1
    return 0


def cmd_check(a) -> int:
    if not (a.issue or a.title or a.body):
        sys.exit("fence: give the issue with --issue FILE or --title/--body")
    raw = _read(a.diff)
    if a.diff.endswith(".json"):
        d = json.loads(raw)
        files = files_from_patches(d["files"]) if "files" in d else parse_diff(d.get("diff", ""))
    else:
        files = parse_diff(raw)
    return _emit(check(_issue(a), files), a)


def cmd_github(a) -> int:
    from .github import GitHub, linked_issues

    m = PR_REF.match(a.pr)
    if not m:
        sys.exit("fence: PR must look like owner/repo#123 or a pull URL")
    repo, num = m.group(1), int(m.group(2))
    gh = GitHub(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"), repo)
    pr = gh.call("GET", f"/pulls/{num}")
    refs = [(repo, a.issue_number)] if a.issue_number else linked_issues(pr.get("body") or "", repo)
    if not refs:
        sys.exit(f"fence: {a.pr} links no issue; pass --issue-number N")
    issue = Issue.merge([gh.issue(n, repo=r) for r, n in refs])
    return _emit(check(issue, gh.pr_files(num)), a)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="fence", description="Fence: flag the parts of a pull request that go beyond what its issue asked for."
    )
    ap.add_argument("--version", action="version", version=f"fence {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def outputs(p):
        p.add_argument("--format", choices=["text", "json", "markdown"], default="text")
        p.add_argument(
            "--fail-over", type=float, default=None, help="exit 1 if the out-of-scope fraction is above this"
        )

    c = sub.add_parser("check", help="check a local diff against an issue")
    c.add_argument(
        "--diff", required=True, help="unified diff file, or JSON with files[{filename,patch}] ('-' = stdin)"
    )
    c.add_argument("--issue", help="issue as JSON {title, body} or Markdown (first line = title)")
    c.add_argument("--title", help="issue title (instead of --issue)")
    c.add_argument("--body", help="issue body (instead of --issue)")
    outputs(c)
    c.set_defaults(func=cmd_check)

    g = sub.add_parser("github", help="check a GitHub PR against the issue it closes (GITHUB_TOKEN optional)")
    g.add_argument("pr", help="owner/repo#123 or https://github.com/owner/repo/pull/123")
    g.add_argument("--issue-number", type=int, help="issue to compare against (default: the ones the PR closes)")
    outputs(g)
    g.set_defaults(func=cmd_github)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    sys.exit(main())
