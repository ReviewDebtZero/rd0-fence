"""Shared statistics and baseline helpers for the Fence benchmark (no network, CPU only)."""

from __future__ import annotations

import math
import re

import numpy as np

CHANGED = re.compile(r"^[+-](?![+-]{2} )(.*)$", re.MULTILINE)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def bootstrap(stat, *arrays, n: int = 2000, seed: int = 0, groups=None) -> tuple[float, float]:
    """Percentile CI. If groups is given, resample whole groups (e.g. repositories) instead of rows."""
    rng = np.random.default_rng(seed)
    arrays = [np.asarray(a) for a in arrays]
    if groups is None:
        m = len(arrays[0])
        idx = (rng.integers(0, m, m) for _ in range(n))
    else:
        groups = np.asarray(groups)
        _, inv = np.unique(groups, return_inverse=True)
        members = np.split(np.argsort(inv, kind="stable"), np.cumsum(np.bincount(inv))[:-1])
        g = len(members)
        idx = (np.concatenate([members[j] for j in rng.integers(0, g, g)]) for _ in range(n))
    vals = []
    for ix in idx:
        try:
            vals.append(stat(*[a[ix] for a in arrays]))
        except ValueError:
            continue
    vals = np.asarray([v for v in vals if not np.isnan(v)])
    return (float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))) if len(vals) else (np.nan, np.nan)


def diff_text(path: str, patch: str | None) -> str:
    """Text a TF-IDF baseline sees for one file: its path plus changed lines."""
    return path.replace("/", " ") + "\n" + "\n".join(CHANGED.findall(patch or ""))


def tfidf_similarity(issue_texts: list[str], diff_texts: list[str]) -> np.ndarray:
    """Cosine similarity between each issue text and its paired diff text, one shared vocabulary."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(
        token_pattern=r"[A-Za-z_][A-Za-z0-9_]{1,}", lowercase=True, sublinear_tf=True, min_df=2, max_features=200_000
    )
    vec.fit(list(issue_texts) + list(diff_texts))
    a = vec.transform(issue_texts)
    b = vec.transform(diff_texts)
    return np.asarray(a.multiply(b).sum(axis=1)).ravel()


def issue_text(issues: list[dict]) -> str:
    return "\n".join(f"{i.get('title') or ''}\n{i.get('body') or ''}" for i in issues)
