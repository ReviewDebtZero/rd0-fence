"""Small GitHub REST client (stdlib only) and helpers to load an issue and a PR's files."""

from __future__ import annotations

import json
import os
import re
import urllib.request

from .diff import FileChange, files_from_patches
from .issue import Issue

API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
CLOSING = re.compile(r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*:?\s+(?:([\w.-]+/[\w.-]+))?#(\d+)", re.IGNORECASE)
ISSUE_URL = re.compile(r"github\.com/([\w.-]+/[\w.-]+)/issues/(\d+)")


class GitHub:
    def __init__(self, token: str | None, repo: str):
        self.token, self.repo = token, repo

    def call(self, method: str, path: str, body: dict | None = None, repo: str | None = None):
        req = urllib.request.Request(
            f"{API}/repos/{repo or self.repo}{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
        )
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"null")

    def pages(self, path: str, limit: int):
        out, page = [], 1
        while len(out) < limit:
            sep = "&" if "?" in path else "?"
            batch = self.call("GET", f"{path}{sep}per_page=100&page={page}")
            if not batch:
                break
            out.extend(batch)
            page += 1
        return out[:limit]

    def pr_files(self, number: int) -> list[FileChange]:
        return files_from_patches(self.pages(f"/pulls/{number}/files", 3000))

    def issue(self, number: int, repo: str | None = None) -> Issue:
        d = self.call("GET", f"/issues/{number}", repo=repo)
        return Issue.from_text(d.get("title") or "", d.get("body") or "", d.get("number"))


def linked_issues(body: str, repo: str) -> list[tuple[str, int]]:
    """Issues a PR body closes (`Fixes #12`, `Closes owner/repo#3`, or a full issue URL)."""
    out = []
    for r, n in CLOSING.findall(body or ""):
        out.append((r or repo, int(n)))
    for r, n in ISSUE_URL.findall(body or ""):
        out.append((r, int(n)))
    seen, uniq = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq
