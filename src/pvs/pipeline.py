"""One entry point for analysis tables, figures, report, and chart-data exports."""
from __future__ import annotations


def run(stage="all"):
    """Run a stage or the full workflow. Set project paths before importing pvs."""
    if stage not in {"all", "tables", "figures", "report", "figure-data", "segments", "story"}:
        raise ValueError(f"Unknown pipeline stage: {stage}")
    if stage in {"all", "tables"}:
        from . import tables
        tables.main()
    if stage in {"all", "figures"}:
        from . import figures
        figures.main()
    if stage in {"all", "report"}:
        from . import report
        report.build()
    if stage in {"all", "figure-data"}:
        from . import figure_data
        figure_data.main()
    if stage == "segments":
        from . import segments
        segments.main()
    if stage == "story":
        from .publication import build
        build()
