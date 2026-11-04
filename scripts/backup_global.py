#!/usr/bin/env python3
"""Backup globale di Spendy: PostgreSQL + configurazione, cifrato con age.

Questo script gira sull'host LXC, non nel container web. Usa Docker Compose per
il dump, `age` per cifrare e, se configurato, `rclone` per la copia offsite.

Uso:
    python3 scripts/backup_global.py backup
    python3 scripts/backup_global.py restore-test

Configurazione tramite variabili d'ambiente (vedi deploy/backup.env.example).
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = Path(os.environ.get("SPENDY_BACKUP_DIR", "/var/backups/spendy"))
STATUS_FILE = Path(
    os.environ.get(
        "SPENDY_BACKUP_STATUS_FILE", str(ROOT / "backup-status" / "status.json")
    )
)
LOCK_FILE = Path(os.environ.get("SPENDY_BACKUP_LOCK", "/run/lock/spendy-backup.lock"))
AGE_RECIPIENT = os.environ.get("SPENDY_AGE_RECIPIENT", "").strip()
AGE_IDENTITY_FILE = os.environ.get("SPENDY_AGE_IDENTITY_FILE", "").strip()
RCLONE_REMOTE = os.environ.get("SPENDY_RCLONE_REMOTE", "").strip()
RCLONE_ARGS = [
    "--timeout",
    "60s",
    "--contimeout",
    "10s",
    "--retries",
    "3",
    "--low-level-retries",
    "3",
]
DOCKER_COMPOSE = shlex.split(
    os.environ.get("SPENDY_DOCKER_COMPOSE", "docker compose")
)
INCREMENTAL_HOURS = int(os.environ.get("SPENDY_BACKUP_INCREMENTAL_HOURS", "48"))
DAILY_KEEP = int(os.environ.get("SPENDY_BACKUP_DAILY_KEEP", "7"))
WEEKLY_KEEP = int(os.environ.get("SPENDY_BACKUP_WEEKLY_KEEP", "4"))
MONTHLY_KEEP = int(os.environ.get("SPENDY_BACKUP_MONTHLY_KEEP", "12"))


def log(message: str) -> None:
    print(message, flush=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime | None = None) -> str:
    return (value or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextlib.contextmanager
def exclusive_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Un altro backup è già in corso.") from exc
        yield


def read_status() -> dict:
    try:
        with STATUS_FILE.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def write_status(**changes) -> None:
    status = read_status()
    status.update(changes)
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATUS_FILE.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(status, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.chmod(temporary, 0o644)
    os.replace(temporary, STATUS_FILE)


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    log("+ " + " ".join(command))
    kwargs.setdefault("text", True)
    try:
        return subprocess.run(command, check=True, **kwargs)
    except subprocess.CalledProcessError as exc:
        output = exc.stderr or exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        detail = output.strip()[-2000:]
        log(f"Comando fallito (exit {exc.returncode}): {detail}")
        raise RuntimeError(
            f"Comando fallito (exit {exc.returncode}): {detail[-500:]}"
        ) from exc


def run_in_db(script: str, **kwargs) -> subprocess.CompletedProcess:
    command = [*DOCKER_COMPOSE, "exec", "-T", "db", "sh", "-c", script]
    kwargs.setdefault("text", True)
    return subprocess.run(command, check=True, **kwargs)


def run_in_db_with_env(script: str, env_name: str, value: str, **kwargs):
    command = [
        *DOCKER_COMPOSE,
        "exec",
        "-T",
        "-e",
        f"{env_name}={value}",
        "db",
        "sh",
        "-c",
        script,
    ]
    kwargs.setdefault("text", True)
    return subprocess.run(command, check=True, **kwargs)


def app_version() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def create_bundle(tmp_dir: Path) -> Path:
    db_dump = tmp_dir / "db.dump"
    log("Dump PostgreSQL ...")
    with db_dump.open("wb") as handle:
        run_in_db(
            'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"',
            stdout=handle,
            cwd=ROOT,
            text=False,
        )
    if db_dump.stat().st_size == 0:
        raise RuntimeError("Il dump del database è vuoto.")

    config_tar = tmp_dir / "config.tar.gz"
    with tarfile.open(config_tar, "w:gz") as archive:
        for name in (".env", "compose.yaml", "VERSION"):
            path = ROOT / name
            if not path.exists():
                raise RuntimeError(f"File di configurazione mancante: {name}")
            archive.add(path, arcname=name)

    manifest = {
        "schema": 1,
        "created_at": iso(),
        "app_version": app_version(),
        "files": {
            "db.dump": sha256(db_dump),
            "config.tar.gz": sha256(config_tar),
        },
    }
    manifest_path = tmp_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    bundle = tmp_dir / "bundle.tar.gz"
    with tarfile.open(bundle, "w:gz") as archive:
        for path in (db_dump, config_tar, manifest_path):
            archive.add(path, arcname=path.name)
    return bundle


def bucket_name(moment: datetime, kind: str) -> str:
    if kind == "daily":
        return f"spendy-{moment.strftime('%Y-%m-%d')}.tar.age"
    if kind == "weekly":
        year, week, _ = moment.isocalendar()
        return f"spendy-{year}-W{week:02d}.tar.age"
    if kind == "monthly":
        return f"spendy-{moment.strftime('%Y-%m')}.tar.age"
    raise ValueError(kind)


def link_or_copy(source: Path, destination: Path) -> None:
    if destination.exists():
        return
    try:
        os.link(source, destination)
    except OSError:
        shutil.copy2(source, destination)


def prune_local(directory: Path, keep: int) -> list[Path]:
    files = sorted(directory.glob("spendy-*.tar.age"), key=lambda p: p.name)
    removed = files[:-keep] if keep > 0 else files
    for path in removed:
        path.unlink(missing_ok=True)
    return removed


def prune_incremental(directory: Path, hours: int) -> list[Path]:
    cutoff = utc_now() - timedelta(hours=hours)
    removed = []
    for path in directory.glob("spendy-*.tar.age"):
        if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed


def remote_path(bucket: str, name: str) -> str:
    return f"{RCLONE_REMOTE.rstrip('/')}/{bucket}/{name}"


def upload(path: Path, bucket: str) -> None:
    if not RCLONE_REMOTE:
        return
    run(
        [
            "rclone",
            "copyto",
            str(path),
            remote_path(bucket, path.name),
            *RCLONE_ARGS,
        ],
        cwd=ROOT,
        capture_output=True,
    )


def prune_remote(bucket: str, keep_names: set[str]) -> None:
    if not RCLONE_REMOTE or not keep_names:
        return
    result = run(
        [
            "rclone",
            "lsf",
            "--files-only",
            f"{RCLONE_REMOTE.rstrip('/')}/{bucket}",
            *RCLONE_ARGS,
        ],
        cwd=ROOT,
        capture_output=True,
    )
    for name in result.stdout.splitlines():
        name = name.strip()
        if not name or name in keep_names:
            continue
        run(
            ["rclone", "deletefile", remote_path(bucket, name), *RCLONE_ARGS],
            cwd=ROOT,
            capture_output=True,
        )


def backup() -> None:
    moment = utc_now()
    try:
        if not AGE_RECIPIENT:
            raise RuntimeError("SPENDY_AGE_RECIPIENT non impostata.")
        if not (ROOT / ".env").exists():
            raise RuntimeError("File .env mancante nella root del progetto.")

        write_status(
            last_run=iso(moment),
            status="running",
            offsite="running",
            last_error=None,
        )

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(BACKUP_DIR, 0o700)
        for bucket in ("incremental", "daily", "weekly", "monthly"):
            directory = BACKUP_DIR / bucket
            directory.mkdir(parents=True, exist_ok=True)
            os.chmod(directory, 0o700)

        result = run(
            [*DOCKER_COMPOSE, "ps", "-q", "db"], cwd=ROOT, capture_output=True
        )
        if not result.stdout.strip():
            raise RuntimeError("Il servizio db non è attivo.")

        name = f"spendy-{timestamp(moment)}.tar.age"
        with tempfile.TemporaryDirectory(prefix="spendy-backup-") as temp:
            tmp_dir = Path(temp)
            bundle = create_bundle(tmp_dir)
            encrypted = tmp_dir / name
            log("Cifratura con age ...")
            run(
                [
                    "age",
                    "--encrypt",
                    "--recipient",
                    AGE_RECIPIENT,
                    "-o",
                    str(encrypted),
                    str(bundle),
                ],
                cwd=ROOT,
            )
            if encrypted.stat().st_size == 0:
                raise RuntimeError("Il file cifrato è vuoto.")

            incremental = BACKUP_DIR / "incremental" / name
            shutil.move(str(encrypted), str(incremental))
            os.chmod(incremental, 0o600)

            created = {"incremental": incremental}
            for kind in ("daily", "weekly", "monthly"):
                destination = BACKUP_DIR / kind / bucket_name(moment, kind)
                link_or_copy(incremental, destination)
                created[kind] = destination

            offsite = "skipped"
            if RCLONE_REMOTE:
                log("Copia offsite con rclone ...")
                for kind, path in created.items():
                    upload(path, kind)
                offsite = "ok"

            removed = prune_incremental(
                BACKUP_DIR / "incremental", INCREMENTAL_HOURS
            )
            removed += prune_local(BACKUP_DIR / "daily", DAILY_KEEP)
            removed += prune_local(BACKUP_DIR / "weekly", WEEKLY_KEEP)
            removed += prune_local(BACKUP_DIR / "monthly", MONTHLY_KEEP)

            if RCLONE_REMOTE:
                keep = {
                    kind: {
                        path.name
                        for path in (BACKUP_DIR / kind).glob("*.tar.age")
                    }
                    for kind in ("incremental", "daily", "weekly", "monthly")
                }
                for kind, names in keep.items():
                    prune_remote(kind, names)

            write_status(
                last_run=iso(moment),
                last_success=iso(),
                status="ok",
                offsite=offsite,
                last_error=None,
            )
            log(f"Backup completato: {incremental} ({len(removed)} file rimossi)")
    except Exception as exc:
        message = str(exc).strip()[:500] or exc.__class__.__name__
        write_status(
            last_run=iso(moment),
            status="failed",
            offsite="failed",
            last_error=message,
        )
        raise


def latest_backup() -> Path:
    candidates = []
    for bucket in ("incremental", "daily", "weekly", "monthly"):
        candidates.extend((BACKUP_DIR / bucket).glob("spendy-*.tar.age"))
    if not candidates:
        raise RuntimeError("Nessun backup disponibile.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def restore_test() -> None:
    moment = utc_now()
    temp_db = f"spendy_restore_test_{timestamp(moment)}".lower()
    write_status(
        restore_test={
            "last_run": iso(moment),
            "status": "running",
            "error": None,
        }
    )

    try:
        if not AGE_IDENTITY_FILE:
            raise RuntimeError("SPENDY_AGE_IDENTITY_FILE non impostata.")
        identity = Path(AGE_IDENTITY_FILE)
        if not identity.exists():
            raise RuntimeError(f"Chiave age non trovata: {identity}")

        source = latest_backup()
        with tempfile.TemporaryDirectory(prefix="spendy-restore-") as temp:
            tmp_dir = Path(temp)
            bundle = tmp_dir / "bundle.tar.gz"
            log(f"Decifratura {source} ...")
            run(
                ["age", "--decrypt", "--identity", str(identity), "-o", str(bundle), str(source)],
                cwd=ROOT,
            )
            with tarfile.open(bundle, "r:gz") as archive:
                members = [
                    member
                    for member in archive.getmembers()
                    if member.name == "db.dump" and member.isfile()
                ]
                if not members:
                    raise RuntimeError("Il backup non contiene db.dump.")
                try:
                    archive.extract(members[0], path=tmp_dir, filter="data")
                except TypeError:
                    # Python < 3.12 non ha il parametro filter.
                    archive.extract(members[0], path=tmp_dir)
            db_dump = tmp_dir / "db.dump"

            log(f"Ripristino in database temporaneo {temp_db} ...")
            run_in_db_with_env(
                'createdb -U "$POSTGRES_USER" "$TMP_DB"',
                "TMP_DB",
                temp_db,
                cwd=ROOT,
            )
            try:
                with db_dump.open("rb") as handle:
                    run_in_db_with_env(
                        'pg_restore -U "$POSTGRES_USER" -d "$TMP_DB" --no-owner --no-privileges',
                        "TMP_DB",
                        temp_db,
                        cwd=ROOT,
                        stdin=handle,
                        text=False,
                    )
                result = run_in_db_with_env(
                    'psql -U "$POSTGRES_USER" -d "$TMP_DB" -Atc "SELECT count(*) FROM accounts_user"',
                    "TMP_DB",
                    temp_db,
                    cwd=ROOT,
                    capture_output=True,
                )
                if not result.stdout.strip().isdigit():
                    raise RuntimeError("Verifica tabelle fallita.")
            finally:
                run_in_db_with_env(
                    'dropdb --if-exists -U "$POSTGRES_USER" "$TMP_DB"',
                    "TMP_DB",
                    temp_db,
                    cwd=ROOT,
                    capture_output=True,
                )

        write_status(
            restore_test={
                "last_run": iso(moment),
                "last_success": iso(),
                "status": "ok",
                "error": None,
            }
        )
        log("Test di ripristino completato.")
    except Exception as exc:
        message = str(exc).strip()[:500] or exc.__class__.__name__
        write_status(
            restore_test={
                "last_run": iso(moment),
                "status": "failed",
                "error": message,
            }
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup globale di Spendy.")
    parser.add_argument("action", choices=("backup", "restore-test"))
    args = parser.parse_args()

    try:
        with exclusive_lock(LOCK_FILE):
            if args.action == "backup":
                backup()
            else:
                restore_test()
    except Exception as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
