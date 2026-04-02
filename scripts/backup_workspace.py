#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "backups"
EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "backups",
}
EXCLUDED_SUFFIXES = {".pyc"}


def iter_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def prune_backups(keep: int) -> None:
    archives = sorted(BACKUP_DIR.glob("rcal-workspace-*.zip"))
    while len(archives) > keep:
        oldest = archives.pop(0)
        oldest.unlink()


def create_backup(keep: int) -> Path:
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_path = BACKUP_DIR / f"rcal-workspace-{timestamp}.zip"
    manifest: dict[str, object] = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "root": str(ROOT),
        "files": [],
    }

    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in iter_files():
            relative = path.relative_to(ROOT)
            archive.write(path, arcname=str(relative))
            cast_files = manifest["files"]
            assert isinstance(cast_files, list)
            cast_files.append(str(relative))
        archive.writestr(
            "backup-manifest.json",
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        )

    prune_backups(keep)
    return archive_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", type=int, default=10)
    args = parser.parse_args()
    archive_path = create_backup(max(args.keep, 1))
    print("======================================")
    print("         RCal Backup Created          ")
    print("======================================")
    print(archive_path)


if __name__ == "__main__":
    main()
