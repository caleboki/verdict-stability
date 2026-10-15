"""Extract the final 0 to 100 score from a model's free text answer."""

import re

# "Score: N" with N a whole number, optionally in bold or followed by "/100".
# The lookahead refuses a decimal (62.5), a longer number (1000), a range
# (60-70, 60 to 70) or a score out of 10 (7/10), so none of them is quietly
# read as a 0 to 100 score.
_SCORE_LINE = re.compile(
    r"score\s*[:=]\s*\**\s*(\d{1,3})(?!\d|[.,]\d|\s*(?:-|–|to)\s*\d|\s*\**\s*/\s*10(?!\d))",
    re.IGNORECASE,
)
_SCORE_MENTION = re.compile(r"score\s*[:=]", re.IGNORECASE)


def parse_score(text: str | None) -> int | None:
    """Return the final 'Score: N' value in the text if 0 <= N <= 100, else None.

    The final mention is used because models sometimes give intermediate
    scores while reasoning before committing to one. If that final score is a
    decimal, a range or out of 10, the answer returns None (a parse failure
    that gets counted) rather than falling back to an earlier whole number or
    being rounded.
    """
    if not text:
        return None
    mentions = list(_SCORE_MENTION.finditer(text))
    if not mentions:
        return None
    final = _SCORE_LINE.match(text, mentions[-1].start())
    if final is None:
        return None
    value = int(final.group(1))
    return value if 0 <= value <= 100 else None
