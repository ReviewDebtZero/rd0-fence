"""What an issue asks for: paths, code names and words a reviewer would match against the diff."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CODE_SPAN = re.compile(r"`([^`\n]{2,200})`")
FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
PATH = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w-]+\.[A-Za-z0-9]{1,8})(?::\d+)?(?![\w/])")
DIRPATH = re.compile(r"(?<![\w.-])((?:[\w-]+/){1,}[\w-]+)/?(?![\w/]|\.\w)")
CAMEL = re.compile(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b|\b[a-z]+(?:[A-Z][a-z0-9]+)+\b")
SNAKE = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")
DOTTED = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9]+")
URL = re.compile(r"https?://[^\s`'\"<>()\[\]]+")
ISSUE_REF = re.compile(r"\b[\w.-]+/[\w.-]+#\d+\b")


def _url_path(m: re.Match) -> str:
    """Keep the repository path of a blob/tree link; other links (issues, docs sites) name no repo paths."""
    url = m.group(0)
    for sep in ("/blob/", "/tree/"):
        if sep in url:
            return " " + url.split(sep, 1)[1].split("/", 1)[-1] + " "
    return " "


SPLIT = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")

_STOP_WORDS = """
a an the and or but if of to in on at by for with from into onto as is are was were be been being this that
these those it its we you they i me my our your their he she them his her not no yes do does did done can could
should would will shall may might must have has had having so than then there here when where which who whom
what why how all any each few more most other some such only own same too very just also about above below over
under again further once both between through during before after up down out off add adds added adding use uses
used using make makes made new old fix fixes fixed fixing issue issues bug bugs error errors problem please need
needs want wants like get gets got set sets work works working currently current expected actual behavior
behaviour feature request support supports file files code line lines change changes changed update updates
updated way thing things one two first second instead e.g eg etc via see note able allow allows
"""
STOP = frozenset(_STOP_WORDS.split())

TEST_HINTS = re.compile(r"\b(tests?|testing|unit ?tests?|spec|coverage|pytest|jest)\b", re.IGNORECASE)
DOC_HINTS = re.compile(r"\b(docs?|documentation|readme|changelog|guide|tutorial|docstring)\b", re.IGNORECASE)
CI_HINTS = re.compile(r"\b(ci|workflows?|github actions?|pipeline|lint(?:er|ing)?|pre-commit|build)\b", re.IGNORECASE)
DEP_HINTS = re.compile(
    r"\b(dependenc(?:y|ies)|upgrade|bump|version|package|requirements?|lock ?file|npm|pip)\b", re.IGNORECASE
)


def split_ident(name: str) -> list[str]:
    out = []
    for part in re.split(r"[_\W]+", name):
        out.extend(t.lower() for t in SPLIT.findall(part))
    return [t for t in out if len(t) > 2]


def stem(w: str) -> str:
    w = w.lower()
    for suf in ("ization", "ations", "ation", "ings", "ing", "ers", "er", "ies", "es", "ed", "ly", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


@dataclass
class Issue:
    title: str = ""
    body: str = ""
    number: int | None = None
    paths: set[str] = field(default_factory=set)
    dirs: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)
    terms: set[str] = field(default_factory=set)
    title_terms: set[str] = field(default_factory=set)
    wants_tests: bool = False
    wants_docs: bool = False
    wants_ci: bool = False
    wants_deps: bool = False

    @classmethod
    def from_text(cls, title: str = "", body: str = "", number: int | None = None) -> Issue:
        it = cls(title=title or "", body=body or "", number=number)
        text = f"{it.title}\n{it.body}"
        text_nourl = ISSUE_REF.sub(" ", URL.sub(_url_path, text))
        spans = CODE_SPAN.findall(text_nourl) + FENCE.findall(text_nourl)
        for p in PATH.findall(text_nourl):
            if not re.fullmatch(r"v?\d+(\.\d+)+", p) and not p.lower().startswith("e.g"):
                it.paths.add(p.strip("./") if p.startswith("./") else p)
        it.dirs = {d for d in DIRPATH.findall(text_nourl) if "/" in d and not d.startswith("http")}
        names = set(CAMEL.findall(text_nourl)) | set(SNAKE.findall(text_nourl))
        for d in DOTTED.findall(text_nourl):
            names.update(d.split("."))
        for s in spans:
            names.update(re.findall(r"[A-Za-z_]\w{2,}", s))
        it.names = {n for n in names if len(n) > 2 and n.lower() not in STOP}
        words = {stem(w) for w in WORD.findall(text_nourl) if len(w) > 2 and w.lower() not in STOP}
        for n in it.names:
            words.update(stem(t) for t in split_ident(n))
        it.terms = {w for w in words if w not in STOP and len(w) > 2}
        title_words = {stem(w) for w in WORD.findall(it.title)}
        for n in set(CAMEL.findall(it.title)) | set(SNAKE.findall(it.title)):
            title_words.update(stem(t) for t in split_ident(n))
        it.title_terms = title_words & it.terms
        it.wants_tests = bool(TEST_HINTS.search(text))
        it.wants_docs = bool(DOC_HINTS.search(text))
        it.wants_ci = bool(CI_HINTS.search(text))
        it.wants_deps = bool(DEP_HINTS.search(text))
        return it

    @classmethod
    def merge(cls, issues: list[Issue]) -> Issue:
        if len(issues) == 1:
            return issues[0]
        out = cls.from_text("\n".join(i.title for i in issues), "\n\n".join(i.body for i in issues))
        out.number = issues[0].number if issues else None
        return out
