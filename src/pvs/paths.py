"""Resolve project files independently of the shell or notebook directory."""
from __future__ import annotations

import os
from pathlib import Path
import tomllib


def project_root():
    configured = os.environ.get("PVS_PROJECT_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    source_root = Path(__file__).resolve().parents[2]
    for candidate in [Path.cwd(), *Path.cwd().parents, source_root]:
        metadata = candidate / "pyproject.toml"
        if metadata.is_file():
            with metadata.open("rb") as stream:
                if tomllib.load(stream).get("project", {}).get("name") == "pvs-thailand":
                    return candidate
    # Installed wheels can be used with a data workspace outside the source repo.
    return Path.cwd()


ROOT = project_root()
DATA = ROOT / "data"
MAPPINGS = DATA / "mappings"
OUTPUT = ROOT / "output"
TABLES = OUTPUT / "tables"
FIGURES = OUTPUT / "figures"
