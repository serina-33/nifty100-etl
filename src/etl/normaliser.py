"""
normaliser.py — Day 02 deliverable
Cleans messy year and ticker values coming from raw Excel extracts.

Functions
---------
normalize_year(raw) -> int | None
normalize_ticker(raw) -> str | None
"""
import re

_YEAR_RE = re.compile(r"(\d{4})")
_SHORT_YEAR_RE = re.compile(r"^(\d{2})$")


def normalize_year(raw) -> int | None:
    """
    Normalizes a wide variety of messy year representations into a
    4-digit int fiscal year (the FIRST year of the fiscal period).

    Accepts:  2023, "2023", " 2023 ", "FY2023", "FY23", "FY2023-24",
              "2023-24", "FY 2023", "2023.0", None, "", "N/A"
    Returns:  int year, or None if it cannot be parsed.
    """
    if raw is None:
        return None
    if isinstance(raw, float) and raw != raw:  # NaN
        return None

    s = str(raw).strip()
    if s == "" or s.upper() in {"N/A", "NA", "NONE", "NULL"}:
        return None

    s = s.upper().replace("FY", "").strip()
    s = s.rstrip(".0") if s.endswith(".0") else s

    # First, try a full 4-digit year anywhere in the string (handles
    # "2023", "2023-24", " 2023 ").
    match = _YEAR_RE.search(s)
    if match:
        year = int(match.group(1))
    else:
        # Fall back to a bare 2-digit shorthand, e.g. "FY23" -> "23",
        # "FY95" -> "95" (after the FY prefix has already been stripped).
        short_match = _SHORT_YEAR_RE.match(s)
        if not short_match:
            return None
        two_digit = int(short_match.group(1))
        year = two_digit + 2000 if two_digit < 70 else two_digit + 1900

    if year < 1900 or year > 2100:
        return None

    return year


def normalize_ticker(raw) -> str | None:
    """
    Normalizes ticker symbols into a clean, uppercase, exchange-suffix-free
    form suitable for use as a stable join key.

    Accepts:  " infy.ns ", "TCS-EQ", "HDFCBANK", "reliance.bo", None, ""
    Returns:  clean uppercase ticker string, or None if empty.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None

    s = s.upper()
    # strip common NSE/BSE exchange suffixes
    for suffix in (".NS", ".BO", "-EQ", "-BE", "-BZ"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]

    s = s.strip()
    # remove any remaining whitespace inside the ticker
    s = re.sub(r"\s+", "", s)

    return s if s else None
