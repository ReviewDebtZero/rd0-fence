"""GitHub Action entry point: comment on a PR with the parts that go beyond its linked issue.

Uses only the GitHub REST API with the workflow's GITHUB_TOKEN. No LLM or paid API calls."""

from __future__ import annotations

import json
import os
import sys
import urllib.error

from .github import GitHub, linked_issues
from .issue import Issue
from .render import MARKER, markdown
from .scope import check


def upsert_comment(gh: GitHub, number: int, body: str | None) -> None:
    """Edit Fence's own marker comment (newest first); anyone can paste the marker, so skip comments we cannot edit."""
    comments = gh.pages(f"/issues/{number}/comments", 300)
    ours = [c for c in reversed(comments) if (c.get("body") or "").startswith(MARKER)]
    clearing = not body
    if clearing:
        if not ours:
            return
        body = MARKER + "\n**Fence:** no out-of-scope parts now."
    for c in ours:
        try:
            gh.call("PATCH", f"/issues/comments/{c['id']}", {"body": body})
            return
        except urllib.error.HTTPError as e:
            if e.code not in (403, 404):
                raise
    if not clearing:
        gh.call("POST", f"/issues/{number}/comments", {"body": body})


def run(event: dict, gh: GitHub, issue_number: int | None = None, min_lines: int = 1) -> str | None:
    pr = event["pull_request"]
    refs = [(gh.repo, issue_number)] if issue_number else linked_issues(pr.get("body") or "", gh.repo)
    # The PR author picks these references; reading other repositories' issues could leak private issue text.
    refs = [(r, n) for r, n in refs if r.lower() == gh.repo.lower()]
    if not refs:
        print("rd0_fence: PR links no issue (use 'Fixes #N' in the description); skipping")
        return None
    issue = Issue.merge([gh.issue(n, repo=r) for r, n in refs])
    rep = check(issue, gh.pr_files(pr["number"]))
    shown = ", ".join(f"#{n}" if r == gh.repo else f"{r}#{n}" for r, n in refs)
    if rep.out_lines < min_lines or not rep.flagged:
        upsert_comment(gh, pr["number"], None)
        return None
    body = markdown(rep, f"issue {shown}")
    upsert_comment(gh, pr["number"], body)
    return body


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"]) as fh:
        event = json.load(fh)
    if "pull_request" not in event:
        print("rd0_fence: not a pull_request event, skipping")
        return 0
    gh = GitHub(os.environ["INPUT_GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"])
    issue = os.environ.get("INPUT_ISSUE") or ""
    body = run(event, gh, int(issue) if issue.strip() else None, int(os.environ.get("INPUT_MIN_LINES") or "1"))
    print(body or "rd0_fence: nothing out of scope")
    return 0


if __name__ == "__main__":
    sys.exit(main())
