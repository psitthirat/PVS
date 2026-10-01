"""Verify the approved release without needing private inputs or dependencies."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "results" / "2026-09"


def main():
    with (RELEASE / "manifest.csv").open(encoding="utf-8", newline="") as stream:
        entries = list(csv.DictReader(stream))
    if not entries:
        raise ValueError("Release manifest is empty")
    listed = set()
    for entry in entries:
        path = ROOT / entry["release_path"]
        resolved = path.resolve()
        if not resolved.is_relative_to(RELEASE.resolve()) or path.is_symlink():
            raise ValueError(f"Invalid release path: {entry['release_path']}")
        if resolved in listed:
            raise ValueError(f"Duplicate release entry: {entry['release_path']}")
        listed.add(resolved)
        content = path.read_bytes()
        if len(content) != int(entry["bytes"]):
            raise ValueError(f"Size mismatch: {entry['release_path']}")
        if hashlib.sha256(content).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {entry['release_path']}")
    actual = {
        path.resolve() for path in RELEASE.rglob("*")
        if path.is_file() and path.name not in {".gitignore", "manifest.csv"}
    }
    if actual != listed:
        raise ValueError("Release contains files that do not match the manifest")
    for path in (ROOT / "notebooks").glob("*.ipynb"):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook.get("cells", []):
            if cell.get("outputs") or cell.get("execution_count") is not None or cell.get("attachments"):
                raise ValueError(f"Clear saved outputs, execution counts, and attachments: {path.name}")
    print(f"Verified {len(entries)} release artifacts; no unlisted files.")
    print("Public notebooks contain no saved outputs, execution counts, or attachments.")


if __name__ == "__main__":
    main()
