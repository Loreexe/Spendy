"""Neutralize CSV formula injection in user-controlled text cells.

Spreadsheets treat a cell starting with ``=``, ``+``, ``-``, ``@``, TAB or CR as
a formula. The export prefixes those cells with an apostrophe, and also values
that already start with an apostrophe so the escape stays reversible. The
archive restore removes one apostrophe when two are present, otherwise it
removes it only when it guards one of the dangerous characters.
"""

DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_text(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(DANGEROUS_PREFIXES) or text.startswith("'"):
        return "'" + text
    return text


def restore_csv_text(value: str) -> str:
    if value.startswith("''"):
        return value[1:]
    if len(value) > 1 and value[0] == "'" and value[1] in DANGEROUS_PREFIXES:
        return value[1:]
    return value
