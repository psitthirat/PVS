"""Check web assets, shared DOCX images, and approved source-table copies."""
from __future__ import annotations

import hashlib
import csv
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def asset(value):
    path = (SITE / value).resolve()
    if not path.is_relative_to(SITE.resolve()) or not path.is_file():
        raise ValueError(f"Missing or invalid public asset: {value}")
    return path


def main():
    story = json.loads(asset("assets/story.json").read_text())
    manifest = json.loads(asset("assets/publication-manifest.json").read_text())
    html = asset("index.html").read_text()
    for name in ("styles.css", "assets/story-data.js", "app.js"):
        expected = f'{name}?v={digest(asset(name))[:16]}'
        if f'"{expected}"' not in html:
            raise ValueError(f'HTML asset version is stale: {name}; refresh asset versions before preview/deploy')
    charts = {item["id"]: item for item in story["charts"]}
    if len(charts) != len(story["charts"]):
        raise ValueError("Duplicate chart IDs")
    for chapter in story["chapters"]:
        for identifier in chapter["chart_ids"]:
            if identifier not in charts:
                raise ValueError(f"Missing chapter chart: {identifier}")
    report_metadata = story["report"]
    embedded = set()
    if report_metadata.get("url") or manifest.get("report"):
        raise ValueError("The full report must be requested by email, not downloaded from the site")
    if report_metadata.get("status") == "verified":
        release = json.loads((ROOT / "content/report-release.json").read_text())
        if release.get("status") != "verified" or release.get("remaining_required_edits") != 0:
            raise ValueError("Report release review is unresolved")
        if not (manifest["report_sha256"] == report_metadata.get("sha256") == release["sha256"]):
            raise ValueError("Reviewed report checksum differs from publication manifest")
        if not (release.get("delivery") == report_metadata.get("delivery") == manifest.get("report_delivery") == "email_request"):
            raise ValueError("Report delivery must remain an email request")
        request = urlsplit(report_metadata.get("request_url", ""))
        if request.scheme != "mailto" or request.path != "peerasit.sit@mahidol.ac.th":
            raise ValueError("Report request must use the approved contact email")
        if release.get("email") != request.path or report_metadata.get("email") != request.path:
            raise ValueError("Report contact email differs from release record")
        if manifest.get("report_request_url") != report_metadata["request_url"]:
            raise ValueError("Report request link differs from publication manifest")
        if not all(parse_qs(request.query).get(field) for field in ("subject", "body")):
            raise ValueError("Report request email must include its subject and message")
        original = ROOT / release["source_report"]
        if original.exists():
            if digest(original) != release["sha256"]:
                raise ValueError("Local author report differs from the reviewed checksum")
            with zipfile.ZipFile(original) as document:
                embedded = {hashlib.sha256(document.read(name)).hexdigest()
                            for name in document.namelist() if name.startswith("word/media/") and not name.endswith("/")}
            for chart in manifest["charts"]:
                if chart["embedded_unchanged_in_report"] != (chart["sha256"] in embedded):
                    raise ValueError(f"Embedded chart status differs from report: {chart['id']}")
    elif report_metadata.get("status") != "awaiting_author_corrections":
        raise ValueError("Missing explicit report status")
    for relative, expected in manifest["source_report_hashes"].items():
        original = ROOT / relative
        if original.exists() and digest(original) != expected:
            raise ValueError(f"Source report changed since publication build: {relative}")
    assert {p["id"] for p in story["parts"]} == {"overview", "private"}
    assert all(c["part"] in {"overview", "private"} for c in story["chapters"])
    opening = story["opening"]
    with asset(opening["source"]).open(encoding="utf-8") as stream:
        national = {r["measure_id"]: r for r in csv.DictReader(stream) if r["group_id"] == "all"}
    for item in opening["items"]:
        row = national["has_usual" if item["id"] == "no_usual" else item["id"]]
        total, count = int(row["N"]), int(row["n"])
        if item["id"] == "no_usual": count = total - count
        if (opening["N"], item["n"], item["percent"]) != (total, count, f"{100 * count / total:.1f}%"):
            raise ValueError(f"Opening graphic differs from verified aggregate: {item['id']}")
    for chart in charts.values():
        png = asset(chart["png"])
        svg = asset(chart["svg"])
        dark_svg = asset(chart["svg_dark"])
        if not chart.get("label") or re.match(r"^รูป\s*\d+", chart["label"]):
            raise ValueError(f"Chart tab needs a descriptive topic: {chart['id']}")
        asset(chart["csv"])
        if digest(png) != chart["sha256"]:
            raise ValueError(f"Chart checksum mismatch: {chart['id']}")
        if chart.get("original_palette"):
            for color in chart["original_palette"]:
                if any(color.lower() not in variant.read_text().lower() for variant in (svg, dark_svg)):
                    raise ValueError(f"Original chart palette changed in a display theme: {chart['id']}")
        if chart["id"] in {"report-figure-04", "report-figure-05", "report-figure-06"}:
            if svg.read_bytes() == dark_svg.read_bytes() or "#101116" not in dark_svg.read_text().lower():
                raise ValueError(f"Report chart lacks a distinct dark display: {chart['id']}")
        if story["credit"] not in svg.read_text() or story["credit"] not in dark_svg.read_text():
            raise ValueError(f"Copyright missing from SVG: {chart['id']}")
        for source in chart.get("source_files", []):
            original = ROOT / source["path"]
            if digest(original) != source["sha256"] or digest(asset(source["asset"])) != source["sha256"]:
                raise ValueError(f"Public aggregate copy differs from source: {source['path']}")
        for table in chart["source_tables"]:
            original = ROOT / "results/2026-09/tables" / f"{table}.csv"
            if digest(original) != digest(asset(f"assets/data/{table}.csv")):
                raise ValueError(f"Public table copy differs from approved source: {table}")
    javascript = asset("assets/story-data.js").read_text()
    if json.loads(javascript.removeprefix("window.PVS_STORY = ").rstrip(";\n")) != story:
        raise ValueError("File-open fallback differs from story JSON")
    with zipfile.ZipFile(asset(story["chart_bundle"])) as archive:
        if any(Path(name).suffix.lower() in {".doc", ".docx", ".pdf"} for name in archive.namelist()):
            raise ValueError("The chart bundle must not include a full report")
        if json.loads(archive.read("story.json")) != story:
            raise ValueError("Chart ZIP story metadata is stale")
        for chart in charts.values():
            for format in ["png", "svg"]:
                path = asset(chart[format])
                if archive.read(path.name) != path.read_bytes():
                    raise ValueError(f"Chart ZIP is stale: {path.name}")
    forbidden = [p for p in SITE.rglob("*") if p.suffix.lower() in {".pkl", ".pickle", ".xlsx", ".ipynb", ".doc", ".docx", ".pdf"}]
    if forbidden:
        raise ValueError(f"Unexpected private/working artifacts in site: {forbidden}")
    print(f"Verified {len(charts)} charts, two-part narrative, report status, source CSVs, original palettes, SVG credits, JSON fallback, and chart ZIP.")


if __name__ == "__main__":
    main()
