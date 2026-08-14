#!/usr/bin/env python3
"""Create a clean, checksummed source archive for a KDAA-AI release."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from kdaa import __version__  # noqa: E402

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "private_data",
    "runs",
    "venv",
    "workspace",
}
EXCLUDED_FILES = {".coverage", ".env"}


def _included_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if path.name in EXCLUDED_FILES:
            continue
        if any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in relative.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_archive(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"kdaa-ai-v{__version__}.zip"
    checksum = output_dir / f"kdaa-ai-v{__version__}.sha256"
    prefix = f"kdaa-ai-v{__version__}"

    files = _included_files()
    manifest = {
        "project": "KDAA-AI",
        "version": __version__,
        "archive_root": prefix,
        "file_count": len(files),
        "files": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in files
        ],
    }

    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in files:
            relative = path.relative_to(ROOT)
            bundle.write(path, Path(prefix) / relative)
        bundle.writestr(
            f"{prefix}/release_manifest.json",
            json.dumps(manifest, indent=2) + "\n",
        )

    archive_digest = _sha256(archive)
    checksum.write_text(f"{archive_digest}  {archive.name}\n", encoding="utf-8")
    return archive, checksum


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist",
        help="Directory for the archive and checksum (default: dist).",
    )
    args = parser.parse_args()
    archive, checksum = create_archive(args.output)
    print(archive)
    print(checksum)


if __name__ == "__main__":
    main()
