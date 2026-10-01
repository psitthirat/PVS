"""Geographic context for the public story; uses only approved aggregate data.

The supplied axes inherit the story renderer's font and background settings.
These functions do not set figure titles, captions, or author copyright notices.
Map-source attribution stays on the exported graphic as required by its source.
"""

from __future__ import annotations

import csv
import json
import math

from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch, Patch

from pvs.paths import ROOT


GEO = ROOT / "content" / "geography"
TABLES = ROOT / "results" / "2026-09" / "tables"
INK = "#252b38"
MUTED = "#68717f"
TEAL = "#bd3346"
ORANGE = "#db8b47"
NO_SAMPLE = "#e3e8e8"


def _read(name: str):
    return json.loads((GEO / name).read_text(encoding="utf-8"))


def _polygons(geometry):
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        yield from geometry["coordinates"]
    else:
        raise ValueError(f"Unsupported map geometry: {geometry['type']}")


def _draw_feature(ax, feature, *, facecolor, edgecolor, linewidth=0.35, zorder=1, hatch=None):
    """Draw polygon rings (including holes) without an optional GIS dependency."""
    for polygon in _polygons(feature["geometry"]):
        vertices = []
        codes = []
        for ring in polygon:
            if len(ring) < 4:
                continue
            vertices.extend(ring)
            codes.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(ring) - 2)
                         + [MplPath.CLOSEPOLY])
        if vertices:
            ax.add_patch(PathPatch(MplPath(vertices, codes), facecolor=facecolor,
                                   edgecolor=edgecolor, linewidth=linewidth,
                                   zorder=zorder, joinstyle="round", hatch=hatch))


def _sample_rows():
    """Join public Thai names to stable administrative ISO codes; fail on drift."""
    names = {r["name_th"]: r for r in _read("sampled-provinces.json")}
    with (TABLES / "T10_planned_vs_achieved_region.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    result = []
    for row in rows:
        entry = dict(names[row["Province sampled"]])
        entry["health_region"] = int(row["Health region"])
        entry["achieved_total"] = int(row["Achieved total"])
        result.append(entry)
    if len(result) != 13 or len({r["iso"] for r in result}) != 13:
        raise ValueError("Expected thirteen distinct sampled provinces")
    return sorted(result, key=lambda row: row["health_region"])


def draw_thailand(ax):
    """Province sample coverage and achieved counts, not province prevalence.

    The map has all 77 province units; grey indicates no sample. Numbers on the
    map identify health regions and correspond to the compact table at right.
    A typical export is 11.5 × 7 inches, with a copyright footer below the axes.
    """
    rows = _sample_rows()
    sampled = {row["iso"]: row for row in rows}
    palette = LinearSegmentedColormap.from_list("pvs_sample", ["#f2cecb", "#a1253c"])
    scale = Normalize(vmin=80, vmax=210)
    bins = [(80, 120, 100), (120, 160, 140), (160, 180, 170), (180, 211, 195)]
    for feature in _read("thailand-provinces.geojson")["features"]:
        row = sampled.get(feature["properties"]["iso"])
        fill = NO_SAMPLE
        if row:
            midpoint = next(mid for low, high, mid in bins
                            if low <= row["achieved_total"] < high)
            fill = palette(scale(midpoint))
        _draw_feature(ax, feature, facecolor=fill, edgecolor="white", linewidth=0.45)

    # Three central provinces are close together; leader lines keep their
    # region identifiers readable without changing the administrative shapes.
    offsets = {4: (11, 12), 6: (16, -10), 13: (-15, -9)}
    for row in rows:
        region = row["health_region"]
        offset = offsets.get(region, (0, 0))
        ax.annotate(str(region), (row["label_lon"], row["label_lat"]),
                    xytext=offset, textcoords="offset points", ha="center", va="center",
                    color="white", weight="bold", fontsize=8.5, zorder=5,
                    bbox={"boxstyle": "circle,pad=0.18", "fc": INK, "ec": "white", "lw": 0.6},
                    arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.8}
                    if offset != (0, 0) else None)

    x_region, x_province, x_count = 0.61, 0.65, 0.965
    ax.text(x_region, 0.955, "เขต", transform=ax.transAxes, color=MUTED, fontsize=10)
    ax.text(x_province, 0.955, "จังหวัดที่เก็บตัวอย่าง", transform=ax.transAxes,
            color=MUTED, fontsize=10)
    ax.text(x_count, 0.955, "คน", transform=ax.transAxes, color=MUTED, fontsize=10, ha="right")
    for index, row in enumerate(rows):
        y = 0.903 - index * 0.053
        ax.text(x_region, y, str(row["health_region"]), transform=ax.transAxes,
                color=MUTED, fontsize=10.5, va="center")
        ax.text(x_province, y, row["name_th"], transform=ax.transAxes,
                color=INK, fontsize=11, va="center")
        ax.text(x_count, y, f"{row['achieved_total']:,}", transform=ax.transAxes,
                color=INK, weight="bold", fontsize=11, ha="right", va="center")
    ax.plot([x_region, x_count], [0.235, 0.235], transform=ax.transAxes,
            color="#b9c8cd", lw=0.7)
    ax.text(x_province, 0.205, "รวม", transform=ax.transAxes, color=INK, fontsize=12)
    ax.text(x_count, 0.205, f"{sum(r['achieved_total'] for r in rows):,}",
            transform=ax.transAxes, color=TEAL, fontsize=14, weight="bold", ha="right")

    handles = [Patch(facecolor=palette(scale(value)), edgecolor="none", label=label)
               for value, label in [(100, "80–119"), (140, "120–159"),
                                    (170, "160–179"), (195, "180–210")]]
    handles.append(Patch(facecolor=NO_SAMPLE, edgecolor="none", label="ไม่ได้เก็บตัวอย่าง"))
    ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.60, 0.012),
              ncol=2, frameon=False, fontsize=8.3, title="จำนวนผู้ตอบ (คน)",
              title_fontsize=10, labelcolor=INK, handlelength=1.1, columnspacing=1.4)
    ax.text(0.02, -0.045, "© OpenStreetMap contributors · geoBoundaries / Wambacher · ODbL 1.0",
            transform=ax.transAxes, color=MUTED, fontsize=7.2, clip_on=False)
    ax.set_xlim(96.6, 116)
    ax.set_ylim(4.6, 21)
    ax.set_aspect(1 / math.cos(math.radians(13)))
    ax.axis("off")
    return {"sampled_provinces": len(rows), "respondents": sum(r["achieved_total"] for r in rows),
            "source": "T10_planned_vs_achieved_region.csv"}


def draw_world(ax, values, *, vmax=100, mendoza=None):
    """Outcome map of the surveyed settings; unsurveyed polygons remain grey.

    Values are descriptive, with differing sample frames, periods and weights.
    Argentina's value describes Mendoza, so the national polygon is not filled.
    """
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import LinearSegmentedColormap
    palette = LinearSegmentedColormap.from_list("pvs_world", ["#fbe6e1", "#e78e83", "#b62d43", "#641d36"])
    scale = Normalize(vmin=0, vmax=vmax)
    labels = {}
    for feature in _read("world-countries.geojson")["features"]:
        props = feature["properties"]
        iso = props["iso"]
        value = values.get(iso)
        fill = palette(scale(value)) if value is not None and iso != "ARG" else NO_SAMPLE
        _draw_feature(ax, feature, facecolor=fill, edgecolor="white", linewidth=0.35,
                      zorder=2 if value is not None else 1)
        if iso in values:
            labels[iso] = (props["label_lon"], props["label_lat"])
        if iso == "THA":
            _draw_feature(ax, feature, facecolor="none", edgecolor=INK, linewidth=0.9, zorder=4, hatch="///")
    # A location marker conveys the subnational sample, not an Argentina estimate.
    if "ARG" in values and mendoza:
        lon, lat = mendoza
        ax.scatter(lon, lat, s=45, facecolor=palette(scale(values["ARG"])), edgecolor=INK, linewidth=.7, zorder=5)
        ax.annotate(f"Mendoza {values['ARG']:.1f}%", (lon, lat), xytext=(-110, -51),
                    fontsize=9, color=INK, ha="center",
                    arrowprops={"arrowstyle": "-", "color": MUTED, "lw": .7})
    if "THA" in labels:
        ax.annotate(f"กลุ่มตัวอย่างไทย\n{values['THA']:.1f}%", labels["THA"], xytext=(125, -17),
                    fontsize=11, weight="bold", color=INK,
                    arrowprops={"arrowstyle": "-", "color": INK, "lw": .8},
                    bbox={"boxstyle": "round,pad=.4", "fc": "white", "ec": "none"})
    cbar = ax.figure.colorbar(ScalarMappable(norm=scale, cmap=palette), ax=ax,
                             orientation="horizontal", fraction=.028, pad=.035, shrink=.42)
    cbar.set_label("ร้อยละของผู้ตอบ", fontsize=10)
    cbar.ax.tick_params(labelsize=9)
    cbar.outline.set_visible(False)
    ax.legend(handles=[Patch(facecolor=NO_SAMPLE, label="ไม่มีค่าประมาณในชุดเปรียบเทียบ")],
              loc="lower left", bbox_to_anchor=(0, -.08), frameon=False, fontsize=8.5)
    ax.text(.01, .015, "Made with Natural Earth · public domain", transform=ax.transAxes,
            color=MUTED, fontsize=7.2)
    ax.set_xlim(-180, 180); ax.set_ylim(-58, 85)
    ax.set_aspect("equal"); ax.axis("off")
    return {"countries_with_values": sorted(values), "argentina_scope": "Mendoza only"}
