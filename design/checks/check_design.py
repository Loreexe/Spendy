#!/usr/bin/env python3
"""Controlli statici mirati del design system Spendy.

Uso: python3 design/checks/check_design.py

Verifica:
  1. token obbligatori presenti in apps/frontend/src/styles/tokens.css (scuro e chiaro);
  2. nessun colore grezzo nei CSS applicativi (fuori da tokens.css) e nei file .tsx;
  3. i valori JS/HTML che devono restare allineati ai token (theme.ts, index.html, manifest);
  4. parità web <-> proiezione Android dei colori mappati (con divergenze note esplicite);
  5. parità dei raggi web <-> Compose;
  6. niente raggi in px o durate in ms scritti a mano nelle dichiarazioni CSS.

Esce con codice 1 se una regola è violata. Le divergenze note sono quelle documentate in
design/platform-matrix.md e design/decisions.md: vengono stampate ma non fanno fallire il
controllo, così non nascondono nuovi scostamenti.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "apps/frontend"
TOKENS = FRONTEND / "src/styles/tokens.css"
ANDROID_THEME = ROOT / "apps/android/app/src/main/java/com/loreexe/spendy/ui/theme"

REQUIRED_TOKENS = [
    "bg0", "bg1", "bg2", "line", "text", "muted",
    "accent", "accent-ink", "accent-hover", "accent-soft",
    "danger", "danger-soft", "warn", "warn-soft", "info", "up", "down",
    "glow1", "glow2",
    "radius", "radius-lg", "radius-pill", "qr-surface",
    "shadow-soft", "overlay", "scroll-shadow", "accent-glow", "warn-line",
    "motion-fast", "motion-base",
]

COLOR_PAIRS = {
    "dark": {
        "bg0": "SpendyBg0Dark",
        "bg1": "SpendyBg1Dark",
        "bg2": "SpendyBg2Dark",
        "line": "SpendyLineDark",
        "text": "SpendyTextDark",
        "muted": "SpendyMutedDark",
        "accent": "SpendyAccentDark",
        "danger": "SpendyDangerDark",
        "warn": "SpendyWarnDark",
        "info": "SpendyInfoDark",
        "up": "SpendyUpDark",
        "down": "SpendyDownDark",
        "accent-soft": "SpendyUpSoftDark",
        "danger-soft": "SpendyDownSoftDark",
    },
    "light": {
        "bg0": "SpendyBg0Light",
        "bg1": "SpendyBg1Light",
        "bg2": "SpendyBg2Light",
        "line": "SpendyLineLight",
        "text": "SpendyTextLight",
        "muted": "SpendyMutedLight",
        "accent": "SpendyAccentLight",
        "danger": "SpendyDangerLight",
        "warn": "SpendyWarnLight",
        "info": "SpendyInfoLight",
        "up": "SpendyUpLight",
        "down": "SpendyDownLight",
        "accent-soft": "SpendyUpSoftLight",
        "danger-soft": "SpendyDownSoftLight",
    },
}

# Divergenze osservate e documentate: non vanno nascoste, ma non sono nuove violazioni.
KNOWN_DRIFT = {
    ("light", "danger"): (
        "SpendyDangerLight usa la palette DC-090 (--down chiaro); tokens.css usa --danger "
        "#B53535 dal 0.8.2. Allineamento proposto P-1 in design/decisions.md."
    ),
    ("light", "warn"): (
        "SpendyWarnLight usa la palette DC-090; tokens.css usa --warn #8A5604 dal 0.8.2. "
        "Allineamento proposto P-1 in design/decisions.md."
    ),
}

HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
CSS_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(")


def parse_tokens() -> dict[str, dict[str, str]]:
    text = TOKENS.read_text()
    themes: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"\[data-theme=\"(dark|light)\"\]\s*\{(.*?)\}", text, re.S):
        theme, block = match.group(1), match.group(2)
        themes[theme] = {
            name: value.strip()
            for name, value in re.findall(r"--([a-z0-9-]+):\s*([^;]+);", block)
        }
    return themes


def normalize_hex(value: str) -> str:
    value = value.strip().lower()
    if len(value) == 4:  # #abc -> #aabbcc
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value


def color_tokens(themes: dict[str, dict[str, str]]) -> set[str]:
    values: set[str] = set()
    for variables in themes.values():
        for value in variables.values():
            if re.fullmatch(r"#[0-9a-fA-F]{3,8}", value):
                values.add(normalize_hex(value))
    return values


def check_required(themes: dict[str, dict[str, str]]) -> list[str]:
    errors = []
    for theme in ("dark", "light"):
        for name in REQUIRED_TOKENS:
            if name not in themes.get(theme, {}):
                errors.append(f"token --{name} mancante nel tema {theme}")
    return errors


def css_files() -> list[pathlib.Path]:
    files = [FRONTEND / "src/styles.css"]
    files += sorted((FRONTEND / "src/styles").glob("*.css"))
    return [f for f in files if f.resolve() != TOKENS.resolve()]


def strip_css_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def check_raw_css_colors() -> list[str]:
    errors = []
    for path in css_files():
        text = strip_css_comments(path.read_text())
        for number, line in enumerate(text.splitlines(), start=1):
            without_vars = re.sub(r"var\([^)]*\)", "", line)
            if CSS_COLOR_RE.search(without_vars):
                rel = path.relative_to(ROOT)
                errors.append(f"colore grezzo in {rel}:{number}: {line.strip()}")
    return errors


def check_raw_tsx_colors() -> list[str]:
    errors = []
    for path in sorted((FRONTEND / "src").rglob("*.tsx")):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            if HEX_RE.search(line):
                rel = path.relative_to(ROOT)
                errors.append(f"colore grezzo in {rel}:{number}: {line.strip()}")
    return errors


def check_raw_css_geometry() -> list[str]:
    errors = []
    for path in css_files():
        rel = path.relative_to(ROOT)
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            stripped = line.strip()
            radius = re.search(r"border-radius:\s*([^;]+);", stripped)
            if radius and "px" in radius.group(1) and "var(" not in radius.group(1):
                errors.append(f"raggio in px in {rel}:{number}: {stripped}")
            duration = re.search(r"(?:transition|animation):\s*([^;]+);", stripped)
            if duration and re.search(r"\d+(?:\.\d+)?ms\b", duration.group(1)):
                errors.append(f"durata in ms in {rel}:{number}: {stripped}")
    return errors


def check_js_mirrors(themes: dict[str, dict[str, str]], values: set[str]) -> list[str]:
    errors = []
    theme_file = FRONTEND / "src/theme.ts"
    html = FRONTEND / "index.html"
    manifest = FRONTEND / "public/manifest.webmanifest"

    for path in (theme_file, html, manifest):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            for found in HEX_RE.findall(line):
                if normalize_hex(found) not in values:
                    rel = path.relative_to(ROOT)
                    errors.append(
                        f"{rel}:{number}: {found} non corrisponde a nessun token di tokens.css"
                    )

    theme_text = theme_file.read_text()
    dark = themes["dark"]
    light = themes["light"]
    theme_color = re.search(
        r"THEME_COLOR[^=]*=\s*\{\s*dark:\s*\"(#[0-9a-fA-F]{6})\",\s*"
        r"light:\s*\"(#[0-9a-fA-F]{6})\"",
        theme_text,
    )
    if not theme_color:
        errors.append("theme.ts: THEME_COLOR non riconosciuto (testo del controllo da aggiornare)")
    else:
        if normalize_hex(theme_color.group(1)) != normalize_hex(dark["bg0"]):
            errors.append("theme.ts: THEME_COLOR.dark diverso da --bg0 scuro")
        if normalize_hex(theme_color.group(2)) != normalize_hex(light["bg0"]):
            errors.append("theme.ts: THEME_COLOR.light diverso da --bg0 chiaro")

    qr_surface = re.search(r"export const QR_SURFACE = \"(#[0-9a-fA-F]{6})\";", theme_text)
    qr_ink = re.search(r"export const QR_INK = \"(#[0-9a-fA-F]{6})\";", theme_text)
    if not qr_surface or not qr_ink:
        errors.append("theme.ts: QR_SURFACE/QR_INK non riconosciuti")
    else:
        if normalize_hex(qr_surface.group(1)) != normalize_hex(dark["qr-surface"]):
            errors.append("theme.ts: QR_SURFACE diverso da --qr-surface")
        if normalize_hex(qr_ink.group(1)) != normalize_hex(dark["bg0"]):
            errors.append("theme.ts: QR_INK diverso da --bg0 scuro")
    return errors


def parse_android_colors() -> dict[str, str]:
    colors: dict[str, str] = {}
    for path in sorted(ANDROID_THEME.glob("*.kt")):
        for name, argb in re.findall(
            r"val\s+(Spendy\w+)\s*=\s*Color\(0x([0-9A-Fa-f]{8})\)", path.read_text()
        ):
            colors[name] = "#" + argb[2:].lower()
    return colors


def check_android_parity(themes: dict[str, dict[str, str]]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    known: list[str] = []
    colors = parse_android_colors()
    for theme, pairs in COLOR_PAIRS.items():
        for token, constant in pairs.items():
            if constant not in colors:
                errors.append(f"Android: costante {constant} mancante")
                continue
            expected = normalize_hex(themes[theme][token])
            actual = colors[constant]
            if expected == actual:
                continue
            reason = KNOWN_DRIFT.get((theme, token))
            if reason:
                known.append(
                    f"{theme}/{token}: token {expected}, {constant} {actual} — {reason}"
                )
            else:
                errors.append(
                    f"Android: {constant} = {actual} diverso da --{token} ({theme}) = {expected}"
                )
    return errors, known


def check_android_shapes(themes: dict[str, dict[str, str]]) -> list[str]:
    errors = []
    theme_text = (ANDROID_THEME / "Theme.kt").read_text()
    shapes = {
        name: int(size)
        for name, size in re.findall(
            r"(small|medium|large)\s*=\s*RoundedCornerShape\((\d+)\.dp\)", theme_text
        )
    }
    expected = {
        "small": int(re.sub(r"px$", "", themes["dark"]["radius"])),
        "medium": int(re.sub(r"px$", "", themes["dark"]["radius"])),
        "large": int(re.sub(r"px$", "", themes["dark"]["radius-lg"])),
    }
    for name, value in expected.items():
        if name not in shapes:
            errors.append(f"Android: forma {name} non riconosciuta in Theme.kt")
        elif shapes[name] != value:
            errors.append(
                f"Android: forma {name} = {shapes[name]}dp diversa da {value}px (web)"
            )
    return errors


def main() -> int:
    if not TOKENS.exists():
        print(f"File token non trovato: {TOKENS}")
        return 1

    themes = parse_tokens()
    values = color_tokens(themes)
    errors: list[str] = []
    known: list[str] = []

    errors += check_required(themes)
    errors += check_raw_css_colors()
    errors += check_raw_tsx_colors()
    errors += check_raw_css_geometry()
    errors += check_js_mirrors(themes, values)
    parity_errors, known = check_android_parity(themes)
    errors += parity_errors
    errors += check_android_shapes(themes)

    print("Spendy — controlli design system")
    print(f"Token obbligatori: {len(REQUIRED_TOKENS)} x 2 temi")
    print(f"Divergenze note documentate: {len(known)}")
    for note in known:
        print(f"  [nota] {note}")

    if errors:
        print(f"\n{len(errors)} violazioni:")
        for error in errors:
            print(f"  [errore] {error}")
        return 1

    print("\nEsito: OK — nessuna violazione delle regole controllate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
