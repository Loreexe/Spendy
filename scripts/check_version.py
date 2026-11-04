#!/usr/bin/env python3
"""Verifica che le versioni dichiarate nel repository siano allineate a VERSION.

`VERSION` alla radice è la fonte di verità. Il backend usa la variabile
`SPENDY_VERSION` (impostata da Docker Compose), mentre frontend, compose e
`.env.example` dichiarano lo stesso valore in punti diversi: senza un controllo
possono divergere e far fallire il ripristino degli archivi (BUG-006).

Uso:
    python3 scripts/check_version.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
COMPOSE_VERSION = re.compile(r"SPENDY_VERSION:\s*\$\{SPENDY_VERSION:-([^}]+)\}")
ENV_VERSION = re.compile(r"^SPENDY_VERSION=(.+)$", re.MULTILINE)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def declared_versions(root: Path) -> dict[str, str]:
    """Restituisce le versioni dichiarate, indicizzate per percorso relativo."""
    package = json.loads(_read(root / "apps" / "frontend" / "package.json"))
    lock = json.loads(_read(root / "apps" / "frontend" / "package-lock.json"))
    if not isinstance(package, dict) or not isinstance(lock, dict):
        raise ValueError("package.json o package-lock.json non contengono un oggetto")
    compose_match = COMPOSE_VERSION.search(_read(root / "compose.yaml"))
    env_match = ENV_VERSION.search(_read(root / ".env.example"))
    versions = {
        "apps/frontend/package.json": str(package.get("version", "")),
        "apps/frontend/package-lock.json": str(lock.get("version", "")),
        "compose.yaml": compose_match.group(1).strip() if compose_match else "",
        ".env.example": env_match.group(1).strip() if env_match else "",
    }
    packages = lock.get("packages")
    if isinstance(packages, dict) and isinstance(packages.get(""), dict):
        versions['apps/frontend/package-lock.json (packages[""])'] = str(
            packages[""].get("version", "")
        )
    return versions


def check(root: Path) -> list[str]:
    """Ritorna l'elenco dei problemi; vuoto se le versioni coincidono."""
    problems: list[str] = []
    try:
        expected = _read(root / "VERSION").strip()
    except OSError as exc:
        return [f"Impossibile leggere VERSION: {exc}"]
    if not SEMVER.match(expected):
        problems.append(f"VERSION non è una versione x.y.z valida: {expected!r}")
    try:
        declared = declared_versions(root)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        return problems + [f"Impossibile leggere le versioni dichiarate: {exc}"]
    for name, value in declared.items():
        if not value:
            problems.append(f"{name}: versione non trovata")
        elif value != expected:
            problems.append(f"{name}: {value} (atteso {expected})")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="radice del repository (default: quella dello script)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="stampa solo in caso di errore",
    )
    args = parser.parse_args()
    problems = check(args.root.resolve())
    if problems:
        for problem in problems:
            print(f"ERRORE versione: {problem}", file=sys.stderr)
        print(
            "Allinea i valori a VERSION prima di procedere (BUG-006).",
            file=sys.stderr,
        )
        return 1
    if not args.quiet:
        print(f"Versioni allineate: {_read(args.root / 'VERSION').strip()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
