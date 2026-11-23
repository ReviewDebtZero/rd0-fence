"""Fence: flags the parts of an agent PR that go beyond what its issue asked for."""

from .diff import FileChange, Hunk, parse_diff
from .issue import Issue
from .scope import Part, Report, check

__all__ = ["FileChange", "Hunk", "Issue", "Part", "Report", "check", "parse_diff"]
__version__ = "0.1.0"
