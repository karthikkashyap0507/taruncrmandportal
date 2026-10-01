#!/usr/bin/env python3
"""Backups for JobsNexGen (portal + CRM), run nightly by cron on the VM.

  python3 deploy/gcp/backup.py backup  [--dest DIR] [--keep-days 14]
  python3 deploy/gcp/backup.py verify  FILE.db.gz
  python3 deploy/gcp/backup.py restore FILE.db.gz TARGET.db [--force]

backup:  takes a consistent online copy of each SQLite database (safe while the
         apps are running), checks its integrity, gzips it, archives uploaded
         documents, and deletes backups older than --keep-days.
restore: verifies the backup, keeps a copy of the current database next to it,
         then replaces it. Stop the app first:  pm2 stop portal-api crm-api
"""
import argparse
import datetime as dt
import gzip
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATABASES = {
    "portal": os.path.join(REPO, "backend", "jobsnexgen.db"),
    "crm": os.path.join(REPO, "crm", "backend", "crm.db"),
}
FILE_DIRS = {
    "portal-files": [os.path.join(REPO, "backend", d) for d in ("private_uploads", "uploads")],
    "crm-files": [os.path.join(REPO, "crm", "backend", d) for d in ("private_uploads", "uploads")],
}


def _integrity_ok(db_path: str) -> bool:
    con = sqlite3.connect(db_path)
    try:
        return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        con.close()


def backup_db(src: str, dest_gz: str) -> dict:
    """Online backup (sqlite3 backup API) -> integrity check -> gzip."""
    with tempfile.TemporaryDirectory() as tmp:
        snapshot = os.path.join(tmp, "snapshot.db")
        source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        if not _integrity_ok(snapshot):
            raise RuntimeError(f"integrity check failed for snapshot of {src}")
        con = sqlite3.connect(snapshot)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        rows = sum(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables)
        con.close()
        with open(snapshot, "rb") as f_in, gzip.open(dest_gz, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out)
    return {"tables": len(tables), "rows": rows, "bytes": os.path.getsize(dest_gz)}


def cmd_backup(dest: str, keep_days: int) -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(dest, exist_ok=True)
    ok = True
    for name, path in DATABASES.items():
        if not os.path.exists(path):
            print(f"[skip] {name}: {path} not found")
            continue
        out = os.path.join(dest, f"{name}-{stamp}.db.gz")
        try:
            info = backup_db(path, out)
            print(f"[ok]   {name}: {out} ({info['tables']} tables, {info['rows']} rows, {info['bytes']} bytes)")
        except Exception as exc:  # keep going so one failure doesn't skip the rest
            ok = False
            print(f"[FAIL] {name}: {exc}")
    for name, dirs in FILE_DIRS.items():
        present = [d for d in dirs if os.path.isdir(d)]
        if not present:
            continue
        out = os.path.join(dest, f"{name}-{stamp}.tar.gz")
        with tarfile.open(out, "w:gz") as tar:
            for d in present:
                tar.add(d, arcname=os.path.relpath(d, REPO))
        print(f"[ok]   {name}: {out}")
    cutoff = dt.datetime.now() - dt.timedelta(days=keep_days)
    for fname in os.listdir(dest):
        fpath = os.path.join(dest, fname)
        if fname.endswith((".db.gz", ".tar.gz")) and dt.datetime.fromtimestamp(os.path.getmtime(fpath)) < cutoff:
            os.remove(fpath)
            print(f"[old]  removed {fname}")
    return 0 if ok else 1


def _ungzip_to_temp(backup_gz: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    with gzip.open(backup_gz, "rb") as f_in, open(path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    return path


def cmd_verify(backup_gz: str) -> int:
    path = _ungzip_to_temp(backup_gz)
    try:
        good = _integrity_ok(path)
        print(f"{'[ok]  ' if good else '[FAIL]'} {backup_gz}: integrity {'ok' if good else 'FAILED'}")
        return 0 if good else 1
    finally:
        os.remove(path)


def cmd_restore(backup_gz: str, target: str, force: bool) -> int:
    path = _ungzip_to_temp(backup_gz)
    try:
        if not _integrity_ok(path):
            print("[FAIL] backup failed its integrity check; nothing was changed")
            return 1
        if os.path.exists(target):
            if not force:
                print(f"[stop] {target} exists. Stop the app, then re-run with --force to replace it.")
                return 1
            keep = f"{target}.before-restore-{dt.datetime.now():%Y%m%d-%H%M%S}"
            shutil.copy2(target, keep)
            print(f"[ok]   current database kept at {keep}")
            for suffix in ("-wal", "-shm"):
                if os.path.exists(target + suffix):
                    os.remove(target + suffix)
        shutil.copy2(path, target)
        print(f"[ok]   restored {backup_gz} -> {target}")
        return 0
    finally:
        os.remove(path)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup")
    b.add_argument("--dest", default=os.path.expanduser("~/backups"))
    b.add_argument("--keep-days", type=int, default=14)
    v = sub.add_parser("verify")
    v.add_argument("file")
    r = sub.add_parser("restore")
    r.add_argument("file")
    r.add_argument("target")
    r.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "backup":
        return cmd_backup(a.dest, a.keep_days)
    if a.cmd == "verify":
        return cmd_verify(a.file)
    return cmd_restore(a.file, a.target, a.force)


if __name__ == "__main__":
    sys.exit(main())
