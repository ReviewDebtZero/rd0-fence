"""Decide, part by part, whether a PR change is inside the scope its issue asked for."""

from __future__ import annotations

import posixpath
import re
from dataclasses import asdict, dataclass, field

from .diff import FileChange, Hunk
from .issue import Issue, split_ident, stem

LOCKS = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock", "cargo.lock", "go.sum",
    "gemfile.lock", "composer.lock", "uv.lock", "bun.lockb", "podfile.lock", "pubspec.lock", "packages.lock.json",
}  # fmt: skip
MANIFESTS = {
    "package.json", "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "pipfile", "cargo.toml",
    "go.mod", "gemfile", "composer.json", "pom.xml", "build.gradle", "build.gradle.kts", "pubspec.yaml",
}  # fmt: skip
CI_PATH = re.compile(
    r"(^|/)(\.github/workflows|\.circleci|\.gitlab-ci\.yml|azure-pipelines|\.travis\.yml|jenkinsfile"
    r"|\.pre-commit-config\.yaml|\.buildkite|\.github/actions)",
    re.IGNORECASE,
)
DOC_PATH = re.compile(
    r"(^|/)(docs?|documentation)/|\.(md|mdx|rst|adoc|txt)$|(^|/)(readme|changelog|changes|history)", re.IGNORECASE
)
TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|testing)/|(^|/)test_[^/]+$|_test\.\w+$|\.(test|spec)\.\w+$", re.IGNORECASE
)
GEN_PATH = re.compile(
    r"(^|/)(dist|build|vendor|node_modules|__snapshots__)/|\.min\.(js|css)$|\.snap$|\.map$", re.IGNORECASE
)
CONFIG_PATH = re.compile(
    r"(^|/)\.(editorconfig|gitignore|gitattributes|prettierrc[^/]*|eslintrc[^/]*|vscode/|idea/|env[^/]*)"
    r"|(^|/)(tsconfig[^/]*\.json|ruff\.toml|\.flake8|tox\.ini|mypy\.ini|dockerfile|docker-compose[^/]*)$",
    re.IGNORECASE,
)
TEST_AFFIX = re.compile(r"^(test_|tests?_)|(_test|_tests|\.test|\.spec|test|spec|tests)$", re.IGNORECASE)


def kind_of(path: str) -> str:
    base = posixpath.basename(path).lower()
    if base in LOCKS:
        return "lockfile"
    if base in MANIFESTS:
        return "manifest"
    if CI_PATH.search(path):
        return "ci"
    if GEN_PATH.search(path):
        return "generated"
    if TEST_PATH.search(path):
        return "test"
    if DOC_PATH.search(path):
        return "docs"
    if CONFIG_PATH.search(path):
        return "config"
    return "code"


def code_stem(path: str) -> str:
    base = posixpath.basename(path).split(".")[0]
    return TEST_AFFIX.sub("", base).lower() or base.lower()


@dataclass
class Part:
    path: str
    kind: str
    lines: int
    in_scope: bool
    reason: str
    hunk: str | None = None
    severity: str = "none"  # none | low | high


@dataclass
class Report:
    parts: list[Part] = field(default_factory=list)
    anchored: bool = False
    issue_numbers: list[int] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return sum(p.lines for p in self.parts if p.kind != "generated")

    @property
    def out_lines(self) -> int:
        return sum(p.lines for p in self.parts if not p.in_scope and p.kind != "generated")

    @property
    def out_fraction(self) -> float:
        return self.out_lines / self.total_lines if self.total_lines else 0.0

    @property
    def flagged(self) -> list[Part]:
        return [p for p in self.parts if not p.in_scope]

    def to_dict(self) -> dict:
        return {
            "out_fraction": round(self.out_fraction, 4),
            "out_lines": self.out_lines,
            "total_lines": self.total_lines,
            "anchored": self.anchored,
            "issues": self.issue_numbers,
            "flagged": [asdict(p) for p in self.flagged],
            "parts": [asdict(p) for p in self.parts],
        }


def _path_tokens(path: str) -> set[str]:
    toks = set()
    for seg in path.split("/"):
        toks.update(stem(t) for t in split_ident(seg.split(".")[0] if "." in seg else seg))
    return toks


IMPORT_LINE = re.compile(
    r"^\s*(?:import|from|#include|use|using|export)\b|\brequire\(|\bimport\(|^\s*\}\s*from\b|^\s*(?:\w+\s+)?\"[\w./@-]+\"\s*$"
)
SHAPED = re.compile(r"_|[a-z][A-Z]|[A-Za-z]\d")


def _names_in(code_names: set[str], issue: Issue, common: set[str], strict: bool = False) -> set[str]:
    """Issue names found in code. Strict (for any identifier in a hunk, not just definitions): case must
    match and the name must look like code (snake_case, camelCase, digits), so plain words do not count."""
    if strict:
        keep = {n for n in issue.names if SHAPED.search(n) and n.lower() not in common}
        return code_names & keep
    low = {n.lower() for n in issue.names} - common
    return {n for n in code_names if n.lower() in low}


def _path_anchor(fc: FileChange, issue: Issue) -> str | None:
    for path in filter(None, [fc.path, fc.old_path]):
        lp = path.lower()
        base = posixpath.basename(lp)
        for p in issue.paths:
            q = p.lower().lstrip("/")
            if lp == q or lp.endswith("/" + q) or ("/" not in q and base == q):
                return f"the issue names `{p}`"
        for d in issue.dirs:
            q = d.lower().strip("/")
            if lp.startswith(q + "/") or ("/" + q + "/") in ("/" + lp):
                return f"it is under `{d}/`, which the issue names"
        st = code_stem(path)
        if len(st) > 3 and st in {n.lower() for n in issue.names}:
            return f"the issue names `{st}`"
    return None


def _file_link(fc: FileChange, issue: Issue, min_terms: int, common: set[str]) -> tuple[str | None, int]:
    """Why this file is in scope (or None), plus a lexical overlap score (title terms count twice)."""
    a = _path_anchor(fc, issue)
    if a:
        return a, 99
    syms, idents = set(), set()
    for h in fc.hunks:
        syms |= h.symbols()
        idents |= h.identifiers()
    hit = sorted(_names_in(syms, issue, common)) or sorted(_names_in(idents, issue, common, strict=True))
    if hit:
        shown = ", ".join(f"`{n}`" for n in hit[:3])
        return f"its changed code touches {shown}, named in the issue", 50
    toks = _path_tokens(fc.path) | {stem(t) for s in syms for t in split_ident(s)}
    overlap = sorted((toks & issue.terms) - common)
    score = sum(2 if t in issue.title_terms else 1 for t in overlap)
    if score >= min_terms:
        return f"its path and changed names share issue terms ({', '.join(overlap[:4])})", score
    return None, score


def _own_terms(fc: FileChange, issue: Issue, common: set[str]) -> set[str]:
    """Issue terms in the file name or the names it defines (not its directory, which neighbours share)."""
    toks = {stem(t) for t in split_ident(code_stem(fc.path))}
    toks |= {stem(t) for h in fc.hunks for s in h.symbols() for t in split_ident(s)}
    return (toks & issue.terms) - common


def _common(issue: Issue, files: list[FileChange]) -> set[str]:
    """Issue names and terms that show up in most changed files (project or product names): not evidence."""
    if len(files) < 3:
        return set()
    names = {n.lower() for n in issue.names}
    seen: dict[str, int] = {}
    for fc in files:
        found = {i.lower() for h in fc.hunks for i in h.identifiers()} & names
        found |= _path_tokens(fc.path) & issue.terms
        for x in found:
            seen[x] = seen.get(x, 0) + 1
    return {x for x, c in seen.items() if c > max(2, 0.6 * len(files))}


def check(issue: Issue, files: list[FileChange]) -> Report:
    """Label every changed file (and formatting-only hunks inside in-scope files) as in or out of scope."""
    rep = Report(issue_numbers=[issue.number] if issue.number else [])
    common = _common(issue, files)
    links: dict[str, str | None] = {}
    scores: dict[str, int] = {}
    judged = [fc for fc in files if kind_of(fc.path) in ("code", "config", "test")]
    for fc in judged:
        links[fc.path], scores[fc.path] = _file_link(fc, issue, 2, common)
    rep.anchored = any(links.values()) or bool(issue.paths or issue.dirs)
    if not rep.anchored:
        for fc in judged:
            links[fc.path], scores[fc.path] = _file_link(fc, issue, 1, common)
        rep.anchored = any(links.values())
    anchored_dirs = {posixpath.dirname(p) for p, why in links.items() if why}
    anchored_stems = {code_stem(p) for p, why in links.items() if why}
    for fc in judged:
        if links[fc.path]:
            continue
        if code_stem(fc.path) in anchored_stems and kind_of(fc.path) == "code":
            links[fc.path] = "the file its in-scope test covers"
        elif _own_terms(fc, issue, common) and posixpath.dirname(fc.path) in anchored_dirs:
            links[fc.path] = "it sits next to an in-scope file and shares an issue term"
    in_mods = {posixpath.basename(p).split(".")[0]: p for p, why in links.items() if why and kind_of(p) == "code"}
    for fc in judged:
        if links[fc.path]:
            continue
        added = "\n".join(line for h in fc.hunks for line in h.added if IMPORT_LINE.search(line))
        used = [m for m in in_mods if len(m) > 3 and m in added]
        if used:
            links[fc.path] = f"it wires in `{in_mods[used[0]]}`, which is in scope"

    in_code = {code_stem(p) for p, why in links.items() if why and kind_of(p) == "code"}
    in_dirs = {posixpath.dirname(p) for p, why in links.items() if why}
    manifests_in = any(kind_of(f.path) == "manifest" for f in files) and issue.wants_deps

    for fc in files:
        k = kind_of(fc.path)
        n = max(fc.changed, 1)
        why = links.get(fc.path)
        if k == "generated":
            rep.parts.append(Part(fc.path, k, n, True, "generated or vendored file; not counted"))
            continue
        if k == "test":
            if why:
                rep.parts.append(Part(fc.path, k, n, True, f"in scope: {why}"))
            elif code_stem(fc.path) in in_code:
                rep.parts.append(Part(fc.path, k, n, True, "tests for a file that is in scope"))
            elif issue.wants_tests and posixpath.dirname(fc.path) in in_dirs | {""}:
                rep.parts.append(Part(fc.path, k, n, True, "the issue asks for tests"))
            elif not rep.anchored:
                rep.parts.append(Part(fc.path, k, n, True, "scope unknown: the issue names nothing concrete"))
            else:
                rep.parts.append(Part(fc.path, k, n, False, "tests for code the issue does not mention", None, "low"))
            continue
        if k == "docs":
            if issue.wants_docs or _path_anchor(fc, issue):
                rep.parts.append(Part(fc.path, k, n, True, "the issue asks for documentation"))
            else:
                rep.parts.append(
                    Part(fc.path, k, n, False, "documentation change the issue did not ask for", None, "low")
                )
            continue
        if k == "ci":
            if issue.wants_ci or _path_anchor(fc, issue) or (_path_tokens(fc.path) & issue.title_terms) - common:
                rep.parts.append(Part(fc.path, k, n, True, "the issue mentions CI or build"))
            else:
                rep.parts.append(
                    Part(
                        fc.path, k, n, False, "changes CI or workflow config; the issue never mentions CI", None, "high"
                    )
                )
            continue
        if k in ("manifest", "lockfile"):
            if issue.wants_deps or _path_anchor(fc, issue) or (k == "lockfile" and manifests_in):
                rep.parts.append(Part(fc.path, k, n, True, "the issue asks for a dependency change"))
            else:
                rep.parts.append(
                    Part(
                        fc.path,
                        k,
                        n,
                        False,
                        "changes dependencies or package metadata; the issue does not ask for that",
                        None,
                        "high",
                    )
                )
            continue
        # code / config
        if why:
            fmt = [h for h in fc.hunks if h.whitespace_only()]
            for h in fmt:
                rep.parts.append(
                    Part(
                        fc.path,
                        k,
                        h.changed,
                        False,
                        "formatting-only edit (same tokens, new whitespace)",
                        _hunk_label(h),
                        "low",
                    )
                )
            rest = n - sum(h.changed for h in fmt)
            if rest > 0 or not fmt:
                rep.parts.append(Part(fc.path, k, max(rest, 1), True, f"in scope: {why}"))
        elif not rep.anchored:
            rep.parts.append(Part(fc.path, k, n, True, "scope unknown: the issue names nothing concrete"))
        elif fc.hunks and all(h.whitespace_only() for h in fc.hunks):
            rep.parts.append(
                Part(fc.path, k, n, False, "formatting-only edit in a file the issue does not mention", None, "low")
            )
        else:
            syms = sorted({s for h in fc.hunks for s in h.symbols()})
            what = f" (changes {', '.join(f'`{s}`' for s in syms[:3])})" if syms else ""
            verb = {"added": "adds", "removed": "deletes", "renamed": "renames"}.get(fc.status, "edits")
            rep.parts.append(
                Part(
                    fc.path,
                    k,
                    n,
                    False,
                    f"{verb} a {k} file{what} that no path, name or term in the issue points to",
                    None,
                    "high",
                )
            )
    return rep


def _hunk_label(h: Hunk) -> str:
    return f"@@ +{h.new_start} {h.header}".strip()
