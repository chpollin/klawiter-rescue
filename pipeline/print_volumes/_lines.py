"""Line roles shared by the probes: page furniture, entry starts and stubs.

The rules are calibrated per part from the data itself, so that one code path
serves three differently laid-out files. A part's continuation indent is the
most frequent x0 of its body lines. A numbered entry start is a line that
opens with a number, optionally prefixed by its address code ("L 464"), sits
left of that indent (hanging indent), and belongs to the part's number
sequence, taken as the longest chain of candidates rising by at most MAX_STEP
per step. The sequence check keeps years and quantities at the line start
("1981 bear the subtitle") out; gaps up to MAX_STEP stay visible in probe 1.
Where a part has no hanging indent, a start may sit at the indent itself.
"""

import re
from collections import Counter
from collections.abc import Callable

from _common import part_of

START_NUMBER = re.compile(r"^(?:[A-R](?:A[12])? ?)?(\d{1,4})([a-z])?(?=[\s.]|$)")
STUB = re.compile(r"^\*{1,5}(?=\s|$)")
DIGITS_ONLY = re.compile(r"^[\divxlcIVXLC]{1,5}$")
MAX_STEP = 50


def is_furniture(line: dict) -> bool:
    """Running heads and page numbers, marked rather than removed."""
    text = line["text"].strip()
    if not text:
        return True
    if line["runs"][0][1] < 11:
        return True
    if line["top"] < 50:
        return True
    return bool(DIGITS_ONLY.match(text)) and (line["top"] < 90 or line["top"] > 700)


def _left_of_indent(body: list[dict]) -> Callable[[dict], bool]:
    indent = Counter(round(ln["x0"]) for ln in body).most_common(1)[0][0]
    hanging = any(ln["x0"] < indent - 5 for ln in body)
    if hanging:
        return lambda ln: ln["x0"] < indent - 5
    return lambda ln: abs(ln["x0"] - indent) <= 2


def annotate(lines: list[dict], volume: str) -> list[dict]:
    """Add part, kind, furniture, margin flag and entry start to each line."""
    parts: dict[str, list[dict]] = {}
    for line in lines:
        line["part"], line["kind"] = part_of(volume, line["page"])
        line["furniture"] = is_furniture(line)
        line["start"] = None
        line["at_margin"] = False
        if line["kind"] == "body" and not line["furniture"]:
            parts.setdefault(line["part"], []).append(line)
    for body in parts.values():
        left = _left_of_indent(body)
        candidates = []
        for line in body:
            line["at_margin"] = left(line)
            match = START_NUMBER.match(line["text"]) if line["at_margin"] else None
            if match:
                candidates.append((int(match.group(1)), match.group(2) or "", line))
        for number, suffix, line in _longest_chain(candidates):
            line["start"] = (number, suffix)
    return lines


def _longest_chain(candidates: list[tuple]) -> list[tuple]:
    """Longest subsequence with steps from 0 to MAX_STEP, starting at most MAX_STEP.

    Unlike a greedy walk, one stray number early in a part cannot block the
    sequence that follows it.
    """
    n = len(candidates)
    best = [1] * n
    back = [-1] * n
    for i in range(n):
        if candidates[i][0] > MAX_STEP:
            best[i] = 0
        for j in range(max(0, i - 400), i):
            step = candidates[i][0] - candidates[j][0]
            if best[j] and 0 <= step <= MAX_STEP and best[j] + 1 > best[i]:
                best[i], back[i] = best[j] + 1, j
    if not n or max(best) == 0:
        return []
    i = max(range(n), key=lambda k: best[k])
    chain = []
    while i != -1:
        chain.append(candidates[i])
        i = back[i]
    return chain[::-1]


def numbered_start(line: dict) -> tuple[int, str] | None:
    return line["start"]


def is_stub(line: dict) -> bool:
    return (
        not line["furniture"]
        and line["kind"] == "body"
        and line["at_margin"]
        and bool(STUB.match(line["text"]))
    )
