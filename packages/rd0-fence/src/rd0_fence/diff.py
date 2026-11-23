"""Parse a unified diff into files and hunks, and pull out the code names each hunk touches."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field

HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
DEF = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?(?:def|class|function|func|fn|interface|type|struct|enum|trait|impl"
    r"|(?:public|private|protected|static|final|abstract)\s[\w<>\[\], ]*?)\s*\(?\s*([A-Za-z_][\w]*)"
)
CODE_TOKEN = re.compile(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`[^`]*`|\S")
ASSIGN_DEF = re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_]\w*)\s*=")


@dataclass
class Hunk:
    old_start: int
    new_start: int
    header: str = ""
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)

    @property
    def changed(self) -> int:
        return len(self.added) + len(self.removed)

    def whitespace_only(self) -> bool:
        """True when the hunk only re-indents or re-wraps lines (same tokens before and after)."""
        if not self.added and not self.removed:
            return False
        toks = lambda xs: [t for x in xs for t in CODE_TOKEN.findall(x)]  # noqa: E731
        return toks(self.added) == toks(self.removed)

    def symbols(self) -> set[str]:
        """Names defined in or enclosing this hunk: the @@ header, plus def/class lines (changed or context)."""
        out: set[str] = set()
        for line in [self.header, *self.context, *self.added, *self.removed]:
            m = DEF.match(line) or ASSIGN_DEF.match(line)
            if m:
                out.add(m.group(1))
        return out

    def identifiers(self) -> set[str]:
        out: set[str] = set()
        for line in self.added + self.removed:
            out.update(IDENT.findall(line))
        return out


@dataclass
class FileChange:
    path: str
    status: str = "modified"  # added | removed | modified | renamed
    old_path: str | None = None
    hunks: list[Hunk] = field(default_factory=list)
    binary: bool = False
    counted: int = 0  # line count reported by GitHub when it omits the patch

    @property
    def added(self) -> int:
        return sum(len(h.added) for h in self.hunks)

    @property
    def removed(self) -> int:
        return sum(len(h.removed) for h in self.hunks)

    @property
    def changed(self) -> int:
        return (self.added + self.removed) or self.counted


def parse_diff(diff: str) -> list[FileChange]:
    """Parse `git diff` output, or plain `diff -u` output with only ---/+++ headers."""
    files: list[FileChange] = []
    cur: FileChange | None = None
    h: Hunk | None = None
    old_left = new_left = 0
    git_header = False
    lines = diff.splitlines()
    for i, raw in enumerate(lines):
        if raw.startswith(("diff --git ", "@@ ")):
            old_left = new_left = 0
        if h is not None and (old_left > 0 or new_left > 0):
            if raw.startswith("+"):
                h.added.append(raw[1:])
                new_left -= 1
            elif raw.startswith("-"):
                h.removed.append(raw[1:])
                old_left -= 1
            elif not raw.startswith("\\"):
                h.context.append(raw[1:])
                old_left -= 1
                new_left -= 1
            continue
        if raw.startswith("diff --git "):
            parts = raw[len("diff --git ") :].split(" b/", 1)
            path = parts[1].strip() if len(parts) == 2 else parts[0].strip()
            old = parts[0][2:].strip() if parts[0].startswith("a/") else None
            cur = FileChange(path=path, old_path=old if old and old != path else None)
            if cur.old_path:
                cur.status = "renamed"
            files.append(cur)
            h, git_header = None, True
        elif raw.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            if git_header:
                continue
            old = _header_path(raw[4:])
            new = _header_path(lines[i + 1][4:])
            if old and new and old.startswith("a/") and new.startswith("b/"):
                old, new = old[2:], new[2:]
            cur = FileChange(path=new or old or "", old_path=old if old and new and old != new else None)
            if new is None:
                cur.status = "removed"
            elif old is None:
                cur.status = "added"
            elif cur.old_path:
                cur.status = "renamed"
            files.append(cur)
            h = None
        elif cur is None or raw.startswith("+++ "):
            continue
        elif raw.startswith("new file mode"):
            cur.status = "added"
        elif raw.startswith("deleted file mode"):
            cur.status = "removed"
        elif raw.startswith(("Binary files", "GIT binary patch")):
            cur.binary = True
        elif raw.startswith("@@"):
            m = HUNK.match(raw)
            if m:
                h = Hunk(int(m.group(1)), int(m.group(3)), (m.group(5) or "").strip())
                old_left = int(m.group(2)) if m.group(2) is not None else 1
                new_left = int(m.group(4)) if m.group(4) is not None else 1
                cur.hunks.append(h)
        elif h is not None and raw.startswith("+"):
            h.added.append(raw[1:])
        elif h is not None and raw.startswith("-"):
            h.removed.append(raw[1:])
        elif h is not None and raw.startswith(" "):
            h.context.append(raw[1:])
    return files


def _header_path(v: str) -> str | None:
    p = v.split("\t", 1)[0].strip()
    if p == "/dev/null":
        return None
    return p


def files_from_patches(items) -> list[FileChange]:
    """Build FileChanges from GitHub API style dicts: {filename, status, patch, previous_filename}."""
    out = []
    for it in items:
        name = it.get("filename") or it.get("path")
        patch = it.get("patch") or ""
        fc = parse_diff(f"diff --git a/{name} b/{name}\n{patch}\n")[0]
        st = it.get("status") or "modified"
        fc.status = {"deleted": "removed"}.get(st, st)
        fc.old_path = it.get("previous_filename")
        fc.binary = not patch and (it.get("changes") or 0) == 0
        if not patch:
            fc.counted = (it.get("additions") or 0) + (it.get("deletions") or 0) or (it.get("changes") or 0)
        out.append(fc)
    return out


def python_symbols(source: str) -> set[str]:
    """Function and class names defined in a Python source file (used when the full file is available)."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
