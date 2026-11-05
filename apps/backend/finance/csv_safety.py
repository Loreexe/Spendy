"""Neutralize CSV formula injection in user-controlled text cells.

Spreadsheets treat a cell starting with ``=``, ``+``, ``-``, ``@``, TAB or CR as
a formula. The export prefixes those cells with an apostrophe; the archive
restore removes the apostrophe only when it guards one of those characters, so
the original value comes back unchanged.
"""

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_text(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(DANGEROUS_PREFIXES):
        return "'" + text
    return text


def restore_csv_text(value: str) -> str:
    if len(value) > 1 and value[0] == "'" and value[1] in DANGEROUS_PREFIXES:
        return value[1:]
    return value
