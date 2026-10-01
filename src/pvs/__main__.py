"""Command-line interface for the PVS Thailand workflow."""
import argparse
import os
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the PVS Thailand analysis workflow.")
    parser.add_argument(
        "stage", nargs="?", default="all",
        choices=["all", "tables", "figures", "report", "figure-data", "segments", "story"],
        help="Workflow stage (default: all). Tables requires private study inputs.",
    )
    parser.add_argument(
        "--project-root", type=Path,
        help="Workspace containing data/ and output/; overrides PVS_PROJECT_ROOT.",
    )
    args = parser.parse_args(argv)
    if args.project_root is not None:
        os.environ["PVS_PROJECT_ROOT"] = str(args.project_root.expanduser().resolve())
    from .pipeline import run
    run(args.stage)


if __name__ == "__main__":
    main()
