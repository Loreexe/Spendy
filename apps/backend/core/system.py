"""Read-only helpers for the admin “Sistema” panel.

The release check is deliberately limited to the public Spendy repository and
never accepts a URL or a tag from the request. This avoids SSRF and keeps the
update check a pure read operation.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings

GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/Loreexe/Spendy/releases/latest"
)
VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    url: str
    published_at: str | None
    notes: str


def parse_version(value: str) -> tuple[int, int, int] | None:
    match = VERSION_RE.match(value.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def is_newer(current: str, latest: str) -> bool:
    current_version = parse_version(current)
    latest_version = parse_version(latest)
    if current_version is None or latest_version is None:
        return False
    return latest_version > current_version


def fetch_latest_release() -> tuple[Release | None, str | None]:
    """Return the latest stable GitHub release, or a user-facing error.

    The endpoint is public, so no token is required. Errors are returned to the
    admin panel instead of being raised: the panel must remain usable when
    GitHub is unreachable or rate-limited.
    """

    request = urllib.request.Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"Spendy/{settings.SPENDY_VERSION}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, "Nessuna release trovata su GitHub."
        if exc.code in (403, 429):
            return None, "Limite di richieste GitHub raggiunto. Riprova più tardi."
        return None, f"GitHub ha risposto con errore {exc.code}."
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None, "GitHub non raggiungibile o risposta non valida."

    if not isinstance(payload, dict):
        return None, "Risposta GitHub non valida."

    if payload.get("prerelease") or payload.get("draft"):
        return None, "L'ultima release è una prerelease o una bozza."

    tag = payload.get("tag_name")
    if not isinstance(tag, str):
        return None, "Release GitHub senza tag valido."

    version = tag.removeprefix("v")
    if parse_version(version) is None:
        return None, "Tag della release non riconosciuto."

    url = payload.get("html_url")
    if not isinstance(url, str) or not url.startswith("https://github.com/"):
        url = "https://github.com/Loreexe/Spendy/releases"

    published_at = payload.get("published_at")
    if not isinstance(published_at, str):
        published_at = None

    notes = payload.get("body")
    if not isinstance(notes, str):
        notes = ""

    return (
        Release(
            version=version,
            tag=tag,
            url=url,
            published_at=published_at,
            notes=notes,
        ),
        None,
    )


def read_backup_status() -> dict | None:
    """Read the host backup status file, if it is mounted.

    The file is produced by the host backup script. It never contains secrets;
    only timestamps, statuses and short error messages.
    """

    path = getattr(settings, "BACKUP_STATUS_FILE", "")
    if not path:
        return None

    try:
        if os.path.getsize(path) > 64 * 1024:
            return {"status": "invalid", "error": "File di stato troppo grande."}
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {"status": "invalid", "error": "File di stato non leggibile."}

    if not isinstance(data, dict):
        return {"status": "invalid", "error": "Formato di stato non valido."}

    allowed = {
        "last_run",
        "last_success",
        "status",
        "offsite",
        "last_error",
        "restore_test",
    }
    return {key: data.get(key) for key in allowed if key in data}
