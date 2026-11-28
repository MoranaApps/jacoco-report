"""
This module parses the unified diff patch of a changed file, as GitHub returns it, into line numbers.
"""

import re
from typing import Optional

# "@@ -a[,b] +c[,d] @@": c is the first line number of the hunk on the new side
_HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def changed_lines_from_patch(patch: str) -> frozenset[int]:
    """
    Gets the new-side line numbers of the lines a patch adds or modifies.

    Parameters:
        patch (str): The patch of one file, as GitHub returns it in the pull request files list.

    Returns:
        frozenset[int]: The line numbers, in the new version of the file, of the added lines.
    """
    changed: set[int] = set()
    new_line: Optional[int] = None  # None until the first hunk header

    # Only "\n" ends a patch line; splitlines() would also split on "\x0c", " " etc. inside a line
    for line in patch.split("\n"):
        header = _HUNK_HEADER.match(line)
        if header:
            new_line = int(header.group(1))
        elif new_line is None or line.startswith("\\"):
            continue  # before the first hunk, or "\ No newline at end of file"
        elif line.startswith("+"):
            changed.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            continue  # removed lines exist only on the old side
        else:
            new_line += 1  # context line

    return frozenset(changed)
