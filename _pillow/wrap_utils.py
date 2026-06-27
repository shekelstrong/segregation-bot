"""
Shared text-wrapping utilities.

``fix_punctuation_wrap`` ensures that punctuation characters (commas, dots,
colons, semicolons, etc.) never appear at the beginning of a wrapped line.
"""
from __future__ import annotations

from typing import List

# Characters that must not start a new line after wrapping.
_PUNCTUATION = frozenset(".,;:!?)}]»'\"–—…")


def fix_punctuation_wrap(lines: List[str]) -> List[str]:
    """Move leading punctuation from a line back to the previous line.

    Operates on a list of plain strings (one per wrapped line).
    Mutates nothing – returns a new list.

    Example
    -------
    >>> fix_punctuation_wrap(["Hello world", ", how are you?"])
    ['Hello world,', 'how are you?']
    """
    if len(lines) <= 1:
        return list(lines)

    result = [lines[0]]
    for line in lines[1:]:
        # Collect leading punctuation characters (possibly followed by a space)
        i = 0
        while i < len(line) and line[i] in _PUNCTUATION:
            i += 1
        if i > 0 and result:
            punct = line[:i]
            rest = line[i:].lstrip()
            result[-1] = result[-1] + punct
            if rest:
                result.append(rest)
            # else: line was only punctuation – absorbed into previous line
        else:
            result.append(line)
    return result
