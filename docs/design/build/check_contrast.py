#!/usr/bin/env python3
"""Verifica il contrasto AA dei token di apps/frontend/src/styles/tokens.css.

Uso: python3 docs/design/build/check_contrast.py
Esce con codice 1 se una coppia scende sotto 4.5:1 (testo piccolo).
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TOKENS = ROOT / "apps/frontend/src/styles/tokens.css"

PAIRS = [
    ("text", "bg0"),
    ("muted", "bg0"),
    ("accent", "bg0"),
    ("danger", "bg0"),
    ("warn", "bg0"),
    ("info", "bg0"),
    ("up", "bg0"),
    ("down", "bg0"),
    ("accent-ink", "accent"),
    ("danger", "danger-soft"),
    ("warn", "warn-soft"),
    ("accent", "accent-soft"),
]


def parse_themes() -> dict[str, dict[str, str]]:
    text = TOKENS.read_text()
    themes: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"\[data-theme=\"(dark|light)\"\]\s*\{(.*?)\}", text, re.S):
        theme, block = match.group(1), match.group(2)
        variables: dict[str, str] = {}
        for name, value in re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block):
            value = value.strip()
            if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                variables[name] = value.lower()
        themes[theme] = variables
    return themes


def luminance(hex_color: str) -> float:
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    high, low = max(la, lb), min(la, lb)
    return (high + 0.05) / (low + 0.05)


def main() -> int:
    themes = parse_themes()
    failures = 0
    for theme in ("dark", "light"):
        variables = themes.get(theme, {})
        print(f"\n{theme}:")
        for fg, bg in PAIRS:
            if fg not in variables or bg not in variables:
                print(f"  {fg} su {bg}: token mancante")
                failures += 1
                continue
            ratio = contrast(variables[fg], variables[bg])
            ok = ratio >= 4.5
            failures += 0 if ok else 1
            print(f"  {fg:10s} su {bg:12s} {ratio:5.2f}:1  {'AA ✓' if ok else 'SOTTO SOGLIA ✗'}")
    if failures:
        print(f"\n{failures} coppie sotto 4.5:1")
        return 1
    print("\nTutte le coppie superano 4.5:1 (AA, testo piccolo).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
