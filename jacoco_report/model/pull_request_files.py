"""
A module that contains the PullRequestFiles class.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PullRequestFiles:
    """
    The files a pull request changes, as GitHub lists them.

    Attributes:
        filenames (list[str]): Every file in the pull request, removed files included, in GitHub's order.
        changed_lines (dict[str, Optional[frozenset[int]]]): Per file, the new-side line numbers the
            pull request adds or modifies. None means the lines are unknown (no patch from GitHub).
            Removed files are absent.
    """

    filenames: list[str] = field(default_factory=list)
    changed_lines: dict[str, Optional[frozenset[int]]] = field(default_factory=dict)
