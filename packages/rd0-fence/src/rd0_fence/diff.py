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
        squash = lambda xs: "".join("".join(x.split()) for x in xs)  # noqa: E731
        return squash(self.added) == squash(self.removed)

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

    @property
    def added(self) -> int:
        return sum(len(h.added) for h in self.hunks)

    @property
    def removed(self) -> int:
        return sum(len(h.removed) for h in self.hunks)

    @property
    def changed(self) -> int:
        return self.added + self.removed


def parse_diff(diff: str) -> list[FileChange]:
    files: list[FileChange] = []
    cur: FileChange | None = None
    h: Hunk | None = None
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            parts = raw[len("diff --git ") :].split(" b/", 1)
            path = parts[1].strip() if len(parts) == 2 else parts[0].strip()
            old = parts[0][2:].strip() if parts[0].startswith("a/") else None
            cur = FileChange(path=path, old_path=old if old and old != path else None)
            if cur.old_path:
                cur.status = "renamed"
            files.append(cur)
            h = None
        elif cur is None:
            continue
        elif raw.startswith("new file mode"):
            cur.status = "added"
        elif raw.startswith("deleted file mode"):
            cur.status = "removed"
        elif raw.startswith(("Binary files", "GIT binary patch")):
            cur.binary = True
        elif raw.startswith(("--- ", "+++ ")):
            continue
        elif raw.startswith("@@"):
            m = HUNK.match(raw)
            if m:
                h = Hunk(int(m.group(1)), int(m.group(3)), (m.group(5) or "").strip())
                cur.hunks.append(h)
        elif h is not None and raw.startswith("+"):
            h.added.append(raw[1:])
        elif h is not None and raw.startswith("-"):
            h.removed.append(raw[1:])
        elif h is not None and raw.startswith(" "):
            h.context.append(raw[1:])
    return files


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
        out.append(fc)
    return out


def python_symbols(source: str) -> set[str]:
    """Function and class names defined in a Python source file (used when the full file is available)."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
